#!/usr/bin/env python3
"""Validate a downloaded or locally built PixCell dataset release."""

from __future__ import annotations

import argparse
import concurrent.futures
import io
import json
import math
import os
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from huggingface_hub import DatasetCard
from PIL import Image

from _shared import (
    LEVELS,
    SAFE_PUBLIC_ID,
    SCHEMA_VERSION,
    ReleaseError,
    canonical_sha256,
    forbidden_release_imports,
    iter_release_files,
    normalized_d4_sha256,
    purity_violations,
    read_json,
    scan_text,
    scan_value_strings,
    sha256_bytes,
    sha256_file,
    verify_checksums,
)
from build_release import ROW_COLUMNS, release_digest_record


EXECUTION_RUNNER = r"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

program_path = Path(sys.argv[1]).resolve()
output_path = Path(sys.argv[2]).resolve()
spec = importlib.util.spec_from_file_location("pixcell_release_program", program_path)
if spec is None or spec.loader is None:
    raise RuntimeError("could not load program")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
device = getattr(module, "device", None)
if not callable(device):
    raise RuntimeError("program has no callable device()")
component = device()
bbox = np.asarray(component.bbox_np(), dtype=float)
if bbox.shape != (2, 2):
    raise RuntimeError(f"unexpected bbox shape: {bbox.shape}")
polygons = component.get_polygons(by="tuple")
polygon_count = sum(len(items) for items in polygons.values())
gds_path = output_path.with_suffix(".gds")
component.write_gds(gds_path, with_metadata=False)
record = {
    "bbox_span_um": (bbox[1] - bbox[0]).tolist(),
    "bbox_um": bbox.tolist(),
    "gds_bytes": gds_path.stat().st_size,
    "polygon_count": polygon_count,
    "port_count": len(component.ports),
    "ports": [
        {
            "center": [float(value) for value in port.dcenter],
            "name": str(port.name),
            "orientation": float(port.orientation),
            "port_type": str(port.port_type),
            "width": float(port.dwidth),
        }
        for port in component.ports
    ],
}
output_path.write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
"""


def _parquet_path(root: Path, level: str) -> Path:
    matches = sorted((root / "data" / level).glob("train-*.parquet"))
    if len(matches) != 1:
        raise ReleaseError(
            f"{level}: expected exactly one Parquet shard, found {len(matches)}"
        )
    return matches[0]


def _embedded_image(
    example_id: str,
    field: str,
    value: Any,
) -> tuple[bytes, Image.Image]:
    if not isinstance(value, dict) or not value.get("bytes"):
        raise ReleaseError(f"{example_id}: {field} is not embedded")
    payload = bytes(value["bytes"])
    try:
        with Image.open(io.BytesIO(payload)) as opened:
            opened.verify()
        opened = Image.open(io.BytesIO(payload)).convert("L")
    except OSError as exc:
        raise ReleaseError(f"{example_id}: invalid {field}") from exc
    extrema = opened.getextrema()
    if extrema[0] == extrema[1]:
        raise ReleaseError(f"{example_id}: blank {field}")
    return payload, opened


def _parse_json_field(example_id: str, field: str, value: str) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"{example_id}: malformed {field}") from exc


def _validate_row(
    row: dict[str, Any],
    *,
    expected_level: str,
    expected_order: int,
) -> dict[str, Any]:
    example_id = str(row.get("id", ""))
    if not example_id:
        raise ReleaseError(f"{expected_level}[{expected_order}]: missing id")
    if SAFE_PUBLIC_ID.fullmatch(example_id) is None:
        raise ReleaseError(f"{example_id!r}: unsafe public id")
    row_hits = scan_value_strings(example_id, row)
    if row_hits:
        raise ReleaseError("; ".join(row_hits))
    if row["schema_version"] != SCHEMA_VERSION:
        raise ReleaseError(f"{example_id}: schema version drift")
    if row["level"] != expected_level.upper():
        raise ReleaseError(f"{example_id}: wrong level {row['level']}")
    if row["curriculum_order"] != expected_order:
        raise ReleaseError(f"{example_id}: non-contiguous curriculum order")
    if row["code_language"] != "python":
        raise ReleaseError(f"{example_id}: unsupported code language")
    lowered_instruction = row["instruction"].lower()
    for field in ("label", "family"):
        value = str(row[field]).strip().lower()
        if value and value in lowered_instruction:
            raise ReleaseError(
                f"{example_id}: class metadata leaked into instruction via {field}"
            )
    code = row["code"]
    try:
        compile(code, f"{example_id}/ground_truth.py", "exec")
    except SyntaxError as exc:
        raise ReleaseError(f"{example_id}: code does not compile: {exc}") from exc
    violations = purity_violations(code)
    if violations:
        raise ReleaseError(f"{example_id}: purity violations: {violations}")
    forbidden = forbidden_release_imports(code)
    if forbidden:
        raise ReleaseError(f"{example_id}: non-standalone imports: {forbidden}")
    if sha256_bytes(code.encode("utf-8")) != row["code_sha256"]:
        raise ReleaseError(f"{example_id}: code hash mismatch")
    for label, text in (
        ("code", code),
        ("instruction", row["instruction"]),
        ("label", row["label"]),
        ("family", row["family"]),
        ("parameters", row["parameters_json"]),
        ("topology", row["topology_json"]),
        ("metadata", row["metadata_json"]),
    ):
        hits = scan_text(f"{example_id}/{label}", text)
        if hits:
            raise ReleaseError("; ".join(hits))
    if (
        "admission_status" in row["metadata_json"]
        or "quarantine" in row["metadata_json"].lower()
    ):
        raise ReleaseError(f"{example_id}: internal admission state leaked")
    for field in (
        "port_signature_json",
        "parameters_json",
        "topology_json",
        "metadata_json",
    ):
        _parse_json_field(example_id, field, row[field])
    footprint = row["footprint_um"]
    if len(footprint) != 2 or any(float(value) <= 0 for value in footprint):
        raise ReleaseError(f"{example_id}: invalid footprint")

    image_bytes, image = _embedded_image(example_id, "image", row["image"])
    target_bytes, _ = _embedded_image(
        example_id,
        "target_image",
        row["target_image"],
    )
    if sha256_bytes(image_bytes) != row["image_sha256"]:
        raise ReleaseError(f"{example_id}: image hash mismatch")
    if sha256_bytes(target_bytes) != row["target_image_sha256"]:
        raise ReleaseError(f"{example_id}: target image hash mismatch")
    d4_hash = normalized_d4_sha256(image)
    if d4_hash != row["normalized_d4_sha256"]:
        raise ReleaseError(f"{example_id}: D4 witness mismatch")
    return {
        "id": example_id,
        "level": expected_level,
        "image_sha256": row["image_sha256"],
        "normalized_d4_sha256": d4_hash,
        "leakage_group_id": row["leakage_group_id"],
        "code": code,
        "footprint_um": [float(value) for value in footprint],
        "port_signature": _parse_json_field(
            example_id,
            "port_signature_json",
            row["port_signature_json"],
        ),
        "topology": _parse_json_field(
            example_id,
            "topology_json",
            row["topology_json"],
        ),
    }


def _collision_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exact: dict[str, list[str]] = defaultdict(list)
    d4: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        exact[row["image_sha256"]].append(row["id"])
        d4[row["normalized_d4_sha256"]].append(row["id"])
    return {
        "exact_duplicate_group_count": sum(len(group) > 1 for group in exact.values()),
        "exact_duplicate_groups": sorted(
            sorted(group) for group in exact.values() if len(group) > 1
        ),
        "d4_equivalent_group_count": sum(len(group) > 1 for group in d4.values()),
        "d4_equivalent_groups": sorted(
            sorted(group) for group in d4.values() if len(group) > 1
        ),
    }


def _expected_port_count(signature: Any) -> int | None:
    if isinstance(signature, dict):
        count = signature.get("count")
        if isinstance(count, int):
            return count
        return None
    if not isinstance(signature, str):
        return None
    pieces = signature.lower().split("x")
    if len(pieces) != 2:
        return 0 if signature.lower() in {"none", "0"} else None
    try:
        return int(pieces[0]) + int(pieces[1])
    except ValueError:
        return None


def _close(left: float, right: float, *, tolerance: float = 0.002) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance)


def _orientation_delta(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def _runtime_ports(
    example_id: str,
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    ports = result.get("ports")
    if not isinstance(ports, list):
        raise ReleaseError(f"{example_id}: execution omitted runtime port records")
    if result.get("port_count") != len(ports):
        raise ReleaseError(f"{example_id}: runtime port records/count disagree")
    normalized: list[dict[str, Any]] = []
    for index, port in enumerate(ports):
        if not isinstance(port, dict):
            raise ReleaseError(f"{example_id}: runtime port {index} is malformed")
        center = port.get("center")
        if (
            not isinstance(center, list)
            or len(center) != 2
            or any(
                not isinstance(value, (int, float)) or not math.isfinite(float(value))
                for value in center
            )
        ):
            raise ReleaseError(
                f"{example_id}: runtime port {index} has an invalid center"
            )
        width = port.get("width")
        if (
            not isinstance(width, (int, float))
            or not math.isfinite(float(width))
            or float(width) <= 0
        ):
            raise ReleaseError(
                f"{example_id}: runtime port {index} has an invalid width"
            )
        orientation = port.get("orientation")
        if not isinstance(orientation, (int, float)) or not math.isfinite(
            float(orientation)
        ):
            raise ReleaseError(
                f"{example_id}: runtime port {index} has an invalid orientation"
            )
        name = port.get("name")
        if not isinstance(name, str) or not name:
            raise ReleaseError(f"{example_id}: runtime port {index} has no name")
        normalized.append(
            {
                "center": [float(value) for value in center],
                "name": name,
                "orientation": float(orientation) % 360.0,
                "port_type": str(port.get("port_type", "")),
                "width": float(width),
            }
        )
    names = [port["name"] for port in normalized]
    if len(names) != len(set(names)):
        raise ReleaseError(f"{example_id}: runtime port names are not unique")
    return normalized


def _validate_l3_ports(
    example_id: str,
    signature: Any,
    ports: list[dict[str, Any]],
) -> None:
    if not isinstance(signature, dict) or not isinstance(signature.get("ports"), list):
        return
    expected_ports = signature["ports"]
    expected_by_name = {
        str(port.get("name")): port
        for port in expected_ports
        if isinstance(port, dict) and port.get("name") is not None
    }
    if len(expected_by_name) != len(expected_ports):
        raise ReleaseError(f"{example_id}: malformed declared L3 port records")
    observed_by_name = {port["name"]: port for port in ports}
    if set(observed_by_name) != set(expected_by_name):
        raise ReleaseError(
            f"{example_id}: runtime L3 port names disagree with declaration"
        )
    declared_names = signature.get("names")
    if isinstance(declared_names, list) and set(map(str, declared_names)) != set(
        observed_by_name
    ):
        raise ReleaseError(f"{example_id}: declared L3 port name list drifted")
    for name, expected in expected_by_name.items():
        observed = observed_by_name[name]
        center = expected.get("center")
        if (
            not isinstance(center, list)
            or len(center) != 2
            or any(
                not isinstance(value, (int, float)) or not math.isfinite(float(value))
                for value in center
            )
        ):
            raise ReleaseError(f"{example_id}: malformed declared L3 port {name}")
        if any(
            not _close(observed_value, float(expected_value))
            for observed_value, expected_value in zip(
                observed["center"],
                center,
                strict=True,
            )
        ):
            raise ReleaseError(f"{example_id}: runtime L3 port {name} center drifted")
        width = expected.get("width")
        orientation = expected.get("orientation")
        if not isinstance(width, (int, float)) or not _close(
            observed["width"],
            float(width),
        ):
            raise ReleaseError(f"{example_id}: runtime L3 port {name} width drifted")
        if (
            not isinstance(orientation, (int, float))
            or _orientation_delta(
                observed["orientation"],
                float(orientation),
            )
            > 0.01
        ):
            raise ReleaseError(
                f"{example_id}: runtime L3 port {name} orientation drifted"
            )


def _validate_l4_ports(
    example_id: str,
    topology: Any,
    result: dict[str, Any],
    ports: list[dict[str, Any]],
) -> None:
    for index, port in enumerate(ports):
        for other in ports[index + 1 :]:
            if (
                all(
                    _close(left, right, tolerance=0.001)
                    for left, right in zip(
                        port["center"],
                        other["center"],
                        strict=True,
                    )
                )
                and _orientation_delta(
                    port["orientation"],
                    other["orientation"],
                )
                <= 1e-6
                and _close(port["width"], other["width"], tolerance=0.001)
            ):
                raise ReleaseError(
                    f"{example_id}: runtime L4 ports contain a duplicated "
                    "physical terminal"
                )
    if not isinstance(topology, dict):
        raise ReleaseError(f"{example_id}: malformed L4 topology contract")
    expected = topology.get("expected_optical_edge_ports")
    if not isinstance(expected, dict):
        raise ReleaseError(f"{example_id}: L4 topology lacks edge-port contract")
    allowed_sides = {"left", "right", "top", "bottom"}
    if any(side not in allowed_sides for side in expected) or any(
        not isinstance(count, int) or count < 0 for count in expected.values()
    ):
        raise ReleaseError(f"{example_id}: malformed L4 edge-port contract")
    bbox = result.get("bbox_um")
    if (
        not isinstance(bbox, list)
        or len(bbox) != 2
        or any(not isinstance(point, list) or len(point) != 2 for point in bbox)
    ):
        raise ReleaseError(f"{example_id}: execution omitted a valid runtime bbox")
    xmin, ymin = (float(value) for value in bbox[0])
    xmax, ymax = (float(value) for value in bbox[1])
    if any(not math.isfinite(value) for value in (xmin, ymin, xmax, ymax)) or not (
        xmin < xmax and ymin < ymax
    ):
        raise ReleaseError(f"{example_id}: execution emitted an invalid runtime bbox")
    side_contract = {
        "left": (0, min, xmin, 1, ymin, ymax, (-1.0, 0.0)),
        "right": (0, max, xmax, 1, ymin, ymax, (1.0, 0.0)),
        "top": (1, max, ymax, 0, xmin, xmax, (0.0, 1.0)),
        "bottom": (1, min, ymin, 0, xmin, xmax, (0.0, -1.0)),
    }
    strongest_side_options: list[tuple[str, list[str]]] = []
    for port in ports:
        angle = math.radians(port["orientation"])
        direction = (math.cos(angle), math.sin(angle))
        tangent = (-direction[1], direction[0])
        endpoints = [
            [
                port["center"][axis] + sign * tangent[axis] * port["width"] / 2
                for axis in (0, 1)
            ]
            for sign in (-1.0, 1.0)
        ]
        matches = []
        for side, (
            axis,
            extreme,
            boundary,
            span_axis,
            span_min,
            span_max,
            outward_normal,
        ) in side_contract.items():
            outward_component = sum(
                value * normal
                for value, normal in zip(direction, outward_normal, strict=True)
            )
            edge_coordinate = extreme(point[axis] for point in endpoints)
            span_coordinates = [point[span_axis] for point in endpoints]
            if (
                _close(edge_coordinate, boundary)
                and max(span_coordinates) >= span_min - 0.002
                and min(span_coordinates) <= span_max + 0.002
                and outward_component > 1e-6
            ):
                matches.append((outward_component, side))
        if not matches:
            raise ReleaseError(
                f"{example_id}: runtime L4 port {port['name']} has no outward "
                "terminal cross-section on the component boundary"
            )
        strongest = max(component for component, _side in matches)
        options = sorted(
            side
            for component, side in matches
            if math.isclose(component, strongest, rel_tol=0.0, abs_tol=1e-9)
        )
        strongest_side_options.append((port["name"], options))

    remaining = {side: int(expected.get(side, 0)) for side in sorted(allowed_sides)}

    def assign(index: int) -> bool:
        if index == len(strongest_side_options):
            return all(count == 0 for count in remaining.values())
        _name, options = strongest_side_options[index]
        for side in options:
            if remaining[side] <= 0:
                continue
            remaining[side] -= 1
            if assign(index + 1):
                return True
            remaining[side] += 1
        return False

    if not assign(0):
        raise ReleaseError(
            f"{example_id}: runtime L4 terminal cross-sections cannot satisfy "
            f"the declared edge-port histogram {dict(expected)}"
        )


def _validate_runtime_port_contract(
    row: dict[str, Any],
    result: dict[str, Any],
) -> None:
    example_id = row["id"]
    expected_ports = _expected_port_count(row["port_signature"])
    if expected_ports is not None and result["port_count"] != expected_ports:
        raise ReleaseError(
            f"{example_id}: port count mismatch "
            f"expected={expected_ports} observed={result['port_count']}"
        )
    ports = _runtime_ports(example_id, result)
    level = row["level"]
    if level == "l3":
        _validate_l3_ports(example_id, row["port_signature"], ports)
    elif level == "l4":
        _validate_l4_ports(example_id, row["topology"], result, ports)


def _execute_one(
    row: dict[str, Any],
    workspace: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    example_id = row["id"]
    task_dir = workspace / example_id
    task_dir.mkdir(parents=True, exist_ok=False)
    program_path = task_dir / "ground_truth.py"
    result_path = task_dir / "result.json"
    program_path.write_text(row["code"], encoding="utf-8")
    runner_path = workspace / "_runner.py"
    environment = dict(os.environ)
    environment.update(
        {
            "MPLCONFIGDIR": str(task_dir / ".mpl"),
            "XDG_CACHE_HOME": str(task_dir / ".cache"),
        }
    )
    completed = subprocess.run(
        [sys.executable, str(runner_path), str(program_path), str(result_path)],
        cwd=task_dir,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout)[-2000:]
        raise ReleaseError(
            f"{example_id}: execution failed ({completed.returncode}): {tail}"
        )
    result = read_json(result_path)
    if result["gds_bytes"] <= 100 or result["polygon_count"] <= 0:
        raise ReleaseError(f"{example_id}: execution emitted empty geometry")
    observed = [float(value) for value in result["bbox_span_um"]]
    if len(observed) != 2 or any(
        not math.isfinite(value) or value <= 0 for value in observed
    ):
        raise ReleaseError(f"{example_id}: execution emitted an invalid GDS bbox")
    _validate_runtime_port_contract(row, result)
    return {"id": example_id, **result}


def execute_programs(
    rows: list[dict[str, Any]],
    *,
    jobs: int,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    with tempfile.TemporaryDirectory(prefix="pixcell-release-execution-") as raw:
        workspace = Path(raw)
        (workspace / "_runner.py").write_text(EXECUTION_RUNNER, encoding="utf-8")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
            futures = {
                pool.submit(_execute_one, row, workspace, timeout_seconds): row["id"]
                for row in rows
            }
            results: list[dict[str, Any]] = []
            for future in concurrent.futures.as_completed(futures):
                example_id = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    for pending in futures:
                        pending.cancel()
                    if isinstance(exc, ReleaseError):
                        raise
                    raise ReleaseError(f"{example_id}: execution error: {exc}") from exc
    return sorted(results, key=lambda item: item["id"])


def validate_release(
    root: Path,
    *,
    execute: bool = False,
    jobs: int = 4,
    timeout_seconds: float = 90.0,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    verify_checksums(root)
    for path in iter_release_files(root):
        if path.suffix.lower() not in {
            ".cff",
            ".json",
            ".md",
            ".py",
            ".txt",
            ".yaml",
            ".yml",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        hits = scan_text(path.relative_to(root).as_posix(), text)
        if hits:
            raise ReleaseError("; ".join(hits))
        if path.suffix == ".py":
            forbidden = forbidden_release_imports(text)
            if forbidden:
                raise ReleaseError(
                    f"{path.relative_to(root)}: forbidden package imports {forbidden}"
                )
    card = DatasetCard.load(str(root / "README.md"))
    card_data = card.data.to_dict()
    if card_data.get("license") != "mit":
        raise ReleaseError("dataset card must declare the MIT license")
    configs = card_data.get("configs")
    if not isinstance(configs, list):
        raise ReleaseError("dataset card has no configurations")
    config_names = [record.get("config_name") for record in configs]
    if config_names != ["all", "core-v1", *LEVELS, "depth-v1"]:
        raise ReleaseError(f"dataset card configuration drift: {config_names}")
    if configs[0].get("default") is not True:
        raise ReleaseError("dataset card's all configuration is not default")
    core_paths = [f"data/{level}/train-*.parquet" for level in LEVELS]
    expected_data_files = {
        "all": [{"split": "train", "path": core_paths}],
        "core-v1": [{"split": "train", "path": core_paths}],
        **{
            level: [
                {
                    "split": "train",
                    "path": f"data/{level}/train-*.parquet",
                }
            ]
            for level in LEVELS
        },
        "depth-v1": [
            {"split": "train", "path": "depth-v1/data/train-*.parquet"},
            {
                "split": "validation",
                "path": "depth-v1/data/validation-*.parquet",
            },
        ],
    }
    for record in configs:
        name = str(record["config_name"])
        if record.get("data_files") != expected_data_files[name]:
            raise ReleaseError(f"dataset card data_files drift for {name}")
    catalog = read_json(root / "metadata" / "catalog.json")
    if catalog.get("schema_version") != SCHEMA_VERSION:
        raise ReleaseError("catalog schema version drift")
    if catalog.get("accepted_only") is not True:
        raise ReleaseError("catalog is not accepted-only")
    if catalog.get("columns") != list(ROW_COLUMNS):
        raise ReleaseError("catalog columns drifted")
    if catalog.get("configurations") != ["all", "core-v1", *LEVELS]:
        raise ReleaseError("catalog configuration drift")
    freeze = read_json(root / "factory" / "core-v1" / "freeze.json")
    if freeze.get("core_name") != "core-v1":
        raise ReleaseError("core-v1 freeze name drift")
    if freeze.get("release_digest_sha256") != catalog.get("release_digest_sha256"):
        raise ReleaseError("catalog differs from frozen core-v1 digest")
    if freeze.get("row_count") != catalog.get("total_rows"):
        raise ReleaseError("catalog differs from frozen core-v1 row count")
    source_bundle = freeze.get("source_bundle")
    if not isinstance(source_bundle, dict):
        raise ReleaseError("core-v1 freeze has no source bundle")
    source_archive = root / str(source_bundle.get("path", ""))
    if not source_archive.is_file():
        raise ReleaseError("core-v1 source archive is missing")
    if sha256_file(source_archive) != source_bundle.get("sha256"):
        raise ReleaseError("core-v1 source archive digest drift")
    grammar = freeze.get("grammar_catalog")
    if not isinstance(grammar, dict):
        raise ReleaseError("core-v1 freeze has no grammar catalog")
    grammar_path = root / str(grammar.get("path", ""))
    if not grammar_path.is_file():
        raise ReleaseError("core-v1 grammar catalog is missing")
    if sha256_file(grammar_path) != grammar.get("sha256"):
        raise ReleaseError("core-v1 grammar catalog digest drift")
    grammar_catalog = read_json(grammar_path)
    if grammar_catalog.get("row_count") != catalog.get(
        "total_rows"
    ) or grammar_catalog.get("representation_count") != catalog.get(
        "total_representation_ids"
    ):
        raise ReleaseError("core-v1 grammar catalog count drift")
    policy = freeze.get("admission_policy")
    if not isinstance(policy, dict):
        raise ReleaseError("core-v1 freeze has no admission policy")
    policy_path = root / str(policy.get("path", ""))
    if not policy_path.is_file() or sha256_file(policy_path) != policy.get("sha256"):
        raise ReleaseError("core-v1 admission policy digest drift")
    reproducibility = freeze.get("reproducibility_report")
    if not isinstance(reproducibility, dict):
        raise ReleaseError("core-v1 freeze has no reproducibility report")
    reproducibility_path = root / str(reproducibility.get("path", ""))
    if not reproducibility_path.is_file() or sha256_file(
        reproducibility_path
    ) != reproducibility.get("sha256"):
        raise ReleaseError("core-v1 reproducibility report digest drift")

    validated: list[dict[str, Any]] = []
    digest_records: list[dict[str, Any]] = []
    level_counts: dict[str, int] = {}
    curriculum_order = 0
    for level in LEVELS:
        path = _parquet_path(root, level)
        table = pq.read_table(path)
        if table.schema.names != list(ROW_COLUMNS):
            raise ReleaseError(f"{level}: Parquet column order/schema drift")
        if b"huggingface" not in (table.schema.metadata or {}):
            raise ReleaseError(f"{level}: Hugging Face feature metadata is missing")
        rows = table.to_pylist()
        digest_records.extend(release_digest_record(row) for row in rows)
        level_counts[level] = len(rows)
        expected_count = catalog["levels"][level]["row_count"]
        if len(rows) != expected_count:
            raise ReleaseError(
                f"{level}: row count {len(rows)} != catalog {expected_count}"
            )
        validated.extend(
            _validate_row(
                row,
                expected_level=level,
                expected_order=curriculum_order + index,
            )
            for index, row in enumerate(rows)
        )
        curriculum_order += len(rows)
    ids = [row["id"] for row in validated]
    if len(ids) != len(set(ids)):
        duplicates = [item for item, count in Counter(ids).items() if count > 1]
        raise ReleaseError(f"duplicate release IDs: {duplicates}")
    if len(validated) != catalog["total_rows"]:
        raise ReleaseError("catalog total row count drift")
    release_digest = canonical_sha256(digest_records)
    if release_digest != catalog["release_digest_sha256"]:
        raise ReleaseError("release digest drift")

    recomputed = _collision_report(validated)
    catalog_collisions = catalog["collision_report"]
    for key in (
        "exact_duplicate_group_count",
        "exact_duplicate_groups",
        "d4_equivalent_group_count",
        "d4_equivalent_groups",
    ):
        if recomputed[key] != catalog_collisions[key]:
            raise ReleaseError(f"collision report drift: {key}")
    for group in recomputed["exact_duplicate_groups"]:
        leakage_ids = {
            row["leakage_group_id"] for row in validated if row["id"] in group
        }
        if len(leakage_ids) != 1:
            raise ReleaseError(f"exact image aliases cross leakage boundaries: {group}")

    execution_results: list[dict[str, Any]] = []
    if execute:
        execution_results = execute_programs(
            validated,
            jobs=jobs,
            timeout_seconds=timeout_seconds,
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "release_digest_sha256": catalog["release_digest_sha256"],
        "total_rows": len(validated),
        "level_counts": level_counts,
        "compiled_programs": len(validated),
        "purity_clean_programs": len(validated),
        "embedded_images": 2 * len(validated),
        "executed_programs": len(execution_results),
        "collision_report": recomputed,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Dataset package root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--execute-programs",
        action="store_true",
        help=(
            "Execute every program and verify emitted GDS and runtime port contracts."
        ),
    )
    parser.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 4))
    parser.add_argument("--timeout-seconds", type=float, default=90.0)
    return parser


def main() -> None:
    args = _parser().parse_args()
    report = validate_release(
        args.root,
        execute=args.execute_programs,
        jobs=args.jobs,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
