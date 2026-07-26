#!/usr/bin/env python3
"""Build the loader-free PixCell L0–L4 Hugging Face release.

This is a maintainer tool.  It consumes the five audited source banks and
materializes canonical Parquet files with embedded PNG bytes.  Downloaders do
not need the source repository or this builder to load the dataset.
"""

from __future__ import annotations

import argparse
import io
import math
import os
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from datasets import Dataset, Features, Image as HFImage, List as HFList, Value
from datasets.utils.logging import disable_progress_bar
from PIL import Image

from _shared import (
    LEVELS,
    SCHEMA_VERSION,
    SAFE_PUBLIC_ID,
    ReleaseError,
    canonical_json,
    canonical_sha256,
    flatten_strings,
    forbidden_release_imports,
    no_absolute_path,
    normalized_d4_sha256,
    primitive_calls,
    purity_violations,
    read_json,
    scan_text,
    scan_value_strings,
    sha256_bytes,
    top_level_parameters,
    write_checksums,
    write_json,
)
from render_galleries import render_release_galleries


BANK_NAMES = {
    "l0": "pool_v8_l0_bank",
    "l1": "pool_v8_l1_bank",
    "l2": "pool_v8_l2_bank",
    "l3": "pool_v8_l3_full120",
    "l4": "pool_v8_l4_core108",
}

PORT_EDGES = ("left", "right", "bottom", "top")

ROW_COLUMNS = (
    "schema_version",
    "id",
    "level",
    "curriculum_order",
    "image",
    "target_image",
    "code",
    "code_language",
    "instruction",
    "label",
    "family",
    "concept_id",
    "representation_id",
    "grammar_id",
    "leakage_group_id",
    "variation_role",
    "primitive_calls",
    "prerequisite_ids",
    "port_signature_json",
    "footprint_um",
    "parameters_json",
    "topology_json",
    "metadata_json",
    "image_sha256",
    "target_image_sha256",
    "code_sha256",
    "normalized_d4_sha256",
    "view_policy",
    "source_dataset_digest_sha256",
    "source_generator_version",
)

NON_DIGEST_PAYLOAD_COLUMNS = frozenset({"image", "target_image", "code"})

L0_PRIMITIVE_PREREQUISITES = {
    "L": "l0_08_l_shape",
    "bend_circular": "l0_11_bend_circular",
    "bend_euler": "l0_10_bend_euler",
    "bend_s": "l0_12_bend_s",
    "bezier": "l0_13_bezier",
    "circle": "l0_02_circle",
    "coupler_straight": "l0_15_coupler_straight",
    "cross": "l0_04_cross",
    "ellipse": "l0_06_ellipse",
    "rectangle": "l0_01_rectangle",
    "regular_polygon": "l0_07_regular_polygon",
    "ring": "l0_03_ring",
    "straight": "l0_09_straight",
    "taper": "l0_14_taper",
    "triangle": "l0_05_triangle",
    "path.Path": "l0_16_path_polyline",
    "path.arc": "l0_18_path_arc",
    "path.euler": "l0_19_path_euler",
    "path.smooth": "l0_20_path_smooth",
    "path.spiral_archimedean": "l0_21_path_spiral",
    "path.straight": "l0_17_path_straight",
    "path.transition": "l0_22_path_transition",
    "extrude_transition": "l0_22_path_transition",
}

DROP_METADATA_KEYS = frozenset(
    {
        "admission_status",
        "manual_visual_approval_status",
        "proposal_workspace",
        "artifact_hashes",
        "path",
        "model_view_path",
        "program_path",
        "selection_path",
    }
)


def release_features() -> Features:
    return Features(
        {
            "schema_version": Value("string"),
            "id": Value("string"),
            "level": Value("string"),
            "curriculum_order": Value("int32"),
            "image": HFImage(),
            "target_image": HFImage(),
            "code": Value("string"),
            "code_language": Value("string"),
            "instruction": Value("string"),
            "label": Value("string"),
            "family": Value("string"),
            "concept_id": Value("string"),
            "representation_id": Value("string"),
            "grammar_id": Value("string"),
            "leakage_group_id": Value("string"),
            "variation_role": Value("string"),
            "primitive_calls": HFList(Value("string")),
            "prerequisite_ids": HFList(Value("string")),
            "port_signature_json": Value("string"),
            "footprint_um": HFList(Value("float64")),
            "parameters_json": Value("string"),
            "topology_json": Value("string"),
            "metadata_json": Value("string"),
            "image_sha256": Value("string"),
            "target_image_sha256": Value("string"),
            "code_sha256": Value("string"),
            "normalized_d4_sha256": Value("string"),
            "view_policy": Value("string"),
            "source_dataset_digest_sha256": Value("string"),
            "source_generator_version": Value("string"),
        }
    )


def release_digest_record(row: dict[str, Any]) -> dict[str, Any]:
    """Return the complete logical row, replacing large payloads by hashes."""

    return {
        key: row[key] for key in ROW_COLUMNS if key not in NON_DIGEST_PAYLOAD_COLUMNS
    }


def _safe_generated_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    forbidden = {
        Path("/").resolve(),
        Path.home().resolve(),
        resolved.parent.resolve(),
    }
    if resolved in forbidden or len(resolved.parts) < 4:
        raise ReleaseError(f"refusing unsafe release output root: {resolved}")
    return resolved


def _resolve_inside(root: Path, relative: str, *, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ReleaseError(f"{label} escapes its source bank: {relative}") from exc
    if not candidate.is_file():
        raise ReleaseError(f"{label} does not exist: {relative}")
    return candidate


def _clean_metadata(value: Any) -> Any:
    """Strip internal path/status bookkeeping while retaining gate evidence."""

    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, child in value.items():
            key_string = str(key)
            if key_string in DROP_METADATA_KEYS:
                continue
            if "quarantine" in key_string.lower() or "admission" in key_string.lower():
                continue
            candidate = _clean_metadata(child)
            if any(scan_text(key_string, text) for text in flatten_strings(candidate)):
                continue
            cleaned[key_string] = candidate
        return cleaned
    if isinstance(value, list):
        return [_clean_metadata(item) for item in value]
    if isinstance(value, tuple):
        return [_clean_metadata(item) for item in value]
    return value


def _label(level: str, record: dict[str, Any]) -> str:
    if record.get("label"):
        return str(record["label"])
    prefix_keys = {
        "l0": ("concept_label", "mode_label"),
        "l1": ("operation_label", "mode_label"),
        "l2": ("composition_label", "mode_label"),
        "l3": ("identity_label", "mode_label"),
        "l4": ("identity_label", "mode_label"),
    }
    pieces: list[str] = []
    for key in prefix_keys[level]:
        value = record.get(key)
        if value and str(value) not in pieces:
            pieces.append(str(value))
    return ": ".join(pieces) if pieces else str(record.get("candidate_id", ""))


def _family(level: str, record: dict[str, Any]) -> str:
    return str(
        record.get("family")
        or record.get("composition_family")
        or {
            "l0": "Primitive catalog",
            "l1": "Primitive operations",
            "l2": "Composed operations",
            "l3": "Hierarchical representations",
            "l4": "Photonic components",
        }[level]
    )


def _concept_id(level: str, record: dict[str, Any]) -> str:
    for key in (
        "concept_id",
        "operation_id",
        "composition_id",
        "identity_id",
        "motif_id",
        "card_id",
        "candidate_id",
    ):
        if record.get(key):
            return str(record[key])
    raise ReleaseError(f"{level}: record has no concept identifier")


def _prerequisites(record: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for key, raw in record.items():
        if key.startswith("prerequisite") or key in {
            "constituent_motifs",
            "ordered_operation_graph",
        }:
            if isinstance(raw, str):
                values.append(raw)
            elif isinstance(raw, list):
                values.extend(str(item) for item in raw if isinstance(item, str))
    return list(dict.fromkeys(values))


def _public_variation_role(record: dict[str, Any]) -> str:
    role = str(record.get("variation_role") or record.get("public_role") or "semantic")
    return "semantic" if role == "semantic_base" else role


def _sidecar(card_dir: Path, name: str) -> Any | None:
    path = card_dir / name
    return read_json(path) if path.is_file() else None


def _parameters(card_dir: Path, code: str) -> dict[str, Any]:
    sidecar = _sidecar(card_dir, "parameters.json")
    if isinstance(sidecar, dict):
        selected = {
            key: sidecar[key]
            for key in ("parameters", "fixed_context")
            if key in sidecar
        }
        if selected:
            return selected
    return top_level_parameters(code)


def _topology(record: dict[str, Any], card_dir: Path) -> Any:
    sidecar = _sidecar(card_dir, "topology_contract.json")
    if sidecar is not None:
        return _clean_metadata(sidecar)
    keys = (
        "topology",
        "port_evidence",
        "structural_emission_evidence",
        "terminal_witness_evidence",
        "analytic_witness_evidence",
    )
    return {key: record[key] for key in keys if key in record}


def _l4_edge_counts(
    example_id: str,
    label: str,
    value: Any,
) -> dict[str, int]:
    if not isinstance(value, dict) or any(key not in PORT_EDGES for key in value):
        raise ReleaseError(f"{example_id}: malformed {label}")
    counts: dict[str, int] = {}
    for edge in PORT_EDGES:
        count = value.get(edge, 0)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ReleaseError(f"{example_id}: malformed {label}")
        counts[edge] = count
    return counts


def _validate_l4_source_port_evidence(
    example_id: str,
    topology: Any,
) -> None:
    """Reject L4 rows whose port contract was not actually executed."""

    if not isinstance(topology, dict):
        raise ReleaseError(f"{example_id}: L4 topology sidecar is missing")
    expected = _l4_edge_counts(
        example_id,
        "expected optical edge-port counts",
        topology.get("expected_optical_edge_ports"),
    )
    evidence = topology.get("runtime_port_evidence")
    if not isinstance(evidence, dict):
        raise ReleaseError(f"{example_id}: L4 runtime port evidence is missing")
    if evidence.get("runtime_inspected") is not True:
        raise ReleaseError(f"{example_id}: L4 ports were not runtime-inspected")
    if evidence.get("source_admission_bound") is not False:
        raise ReleaseError(
            f"{example_id}: L4 port evidence is still source-admission-bound"
        )
    if evidence.get("machine_checks_passed") is not True:
        raise ReleaseError(f"{example_id}: L4 runtime port gate did not pass")
    expected_count = evidence.get("expected_count")
    if (
        not isinstance(expected_count, int)
        or isinstance(expected_count, bool)
        or expected_count != sum(expected.values())
    ):
        raise ReleaseError(f"{example_id}: L4 runtime port count evidence drifted")
    evidence_expected = _l4_edge_counts(
        example_id,
        "runtime expected edge-port counts",
        evidence.get("expected_edge_counts"),
    )
    evidence_observed = _l4_edge_counts(
        example_id,
        "runtime observed edge-port counts",
        evidence.get("observed_edge_counts"),
    )
    if evidence_expected != expected or evidence_observed != expected:
        raise ReleaseError(
            f"{example_id}: L4 runtime edge-port evidence differs from topology"
        )


def _row_metadata(record: dict[str, Any], card_dir: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"source_record": _clean_metadata(record)}
    for filename, key in (
        ("factor_assignment.json", "factor_assignment"),
        ("candidate_evidence.json", "candidate_evidence"),
        ("calibration.json", "calibration"),
    ):
        value = _sidecar(card_dir, filename)
        if value is not None:
            result[key] = _clean_metadata(value)
    return result


def _instruction(card_dir: Path, footprint: list[float]) -> str:
    calibration = _sidecar(card_dir, "calibration.json")
    if not isinstance(calibration, dict):
        raise ReleaseError(f"{card_dir.name}: calibration sidecar is missing")
    scale = calibration.get("scale_px_per_um")
    if not isinstance(scale, list) or len(scale) != 2:
        raise ReleaseError(f"{card_dir.name}: invalid display scale evidence")
    sx, sy = (float(value) for value in scale)
    if any(not math.isfinite(value) or value <= 0 for value in (sx, sy)):
        raise ReleaseError(f"{card_dir.name}: invalid display scale evidence")
    reference = min(sx, sy)
    x_magnification = sx / reference
    y_magnification = sy / reference
    length_um, width_um = footprint
    return (
        "The image is a device-only black-and-white silhouette: BLACK is "
        "material on layer (1,0), WHITE is background. "
        f"Footprint (bounding box): {length_um} x {width_um} micrometers. "
        "DISPLAY NOTE: the overview is normalized for maximum shape visibility; "
        "it is not guaranteed to use physical aspect ratio and has no fixed "
        "absolute pixel scale. Relative overview magnification x:y = "
        f"{x_magnification:.3f}:{y_magnification:.3f}. Use the silhouette for "
        "topology and within-axis proportions, then the stated footprint for "
        "absolute dimensions. Recreate the shown geometry as a primitives-only, "
        "parametric GDSFactory 9.20.7 Python program using the permitted PixCell "
        "catalog. Do not use device-level stencils, raw polygons, raster tracing, "
        "or runtime image reads. Keep function-defining tunables top-level, define "
        "an @gf.cell device, and write device.gds. Output only the Python program."
    )


def _image_bytes(path: Path, *, label: str) -> bytes:
    payload = path.read_bytes()
    try:
        with Image.open(io.BytesIO(payload)) as opened:
            opened.verify()
        with Image.open(io.BytesIO(payload)) as opened:
            grayscale = opened.convert("L")
            extrema = grayscale.getextrema()
            if extrema[0] == extrema[1]:
                raise ReleaseError(f"{label} is visually blank: {path.name}")
    except OSError as exc:
        raise ReleaseError(f"{label} is not a valid image: {path}") from exc
    return payload


def _record_paths(bank: Path, record: dict[str, Any]) -> tuple[Path, Path, Path, Path]:
    card_relative = record.get("path")
    if not isinstance(card_relative, str):
        raise ReleaseError(f"{record.get('candidate_id')}: missing card path")
    card_dir = (bank / card_relative).resolve()
    try:
        card_dir.relative_to(bank.resolve())
    except ValueError as exc:
        raise ReleaseError(f"card path escapes bank: {card_relative}") from exc
    if not card_dir.is_dir():
        raise ReleaseError(f"missing card directory: {card_relative}")
    code_path = _resolve_inside(
        bank,
        str(record.get("program_path") or f"{card_relative}/ground_truth.py"),
        label="program",
    )
    image_path = _resolve_inside(
        bank,
        str(record.get("model_view_path") or f"{card_relative}/model_view.png"),
        label="model view",
    )
    target_path = _resolve_inside(
        bank,
        f"{card_relative}/device_bw.png",
        label="target image",
    )
    return card_dir, code_path, image_path, target_path


def _build_row(
    *,
    level: str,
    order: int,
    bank: Path,
    manifest: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    example_id = str(
        record.get("card_id")
        or record.get("candidate_id")
        or record.get("task_id")
        or ""
    )
    if not example_id:
        raise ReleaseError(f"{level}[{order}]: missing example id")
    if SAFE_PUBLIC_ID.fullmatch(example_id) is None:
        raise ReleaseError(f"{level}[{order}]: unsafe public id: {example_id!r}")
    if record.get("compiled") is not True:
        raise ReleaseError(f"{example_id}: source record is not compiled")
    if record.get("purity_clean") is not True:
        raise ReleaseError(f"{example_id}: source record is not purity-clean")
    if "admission_status" in record and record["admission_status"] not in {
        "accepted",
        "approved",
        "manual_visual_approved",
    }:
        raise ReleaseError(
            f"{example_id}: source admission status is not approved: "
            f"{record['admission_status']}"
        )
    if (
        "manual_visual_approval_status" in record
        and record["manual_visual_approval_status"] != "approved"
    ):
        raise ReleaseError(f"{example_id}: manual visual approval is not approved")
    if any(
        "quarantine" in str(key).lower() and bool(value)
        for key, value in record.items()
    ):
        raise ReleaseError(f"{example_id}: source record is quarantined")

    card_dir, code_path, image_path, target_path = _record_paths(bank, record)
    code = code_path.read_text(encoding="utf-8")
    try:
        compile(code, f"{example_id}/ground_truth.py", "exec")
    except SyntaxError as exc:
        raise ReleaseError(f"{example_id}: program does not compile: {exc}") from exc
    violations = purity_violations(code)
    if violations:
        raise ReleaseError(f"{example_id}: purity violations: {violations}")
    forbidden = forbidden_release_imports(code)
    if forbidden:
        raise ReleaseError(f"{example_id}: non-standalone imports: {forbidden}")
    text_hits = scan_text(f"{example_id}/code", code)
    if text_hits:
        raise ReleaseError("; ".join(text_hits))

    image_bytes = _image_bytes(image_path, label=f"{example_id}/image")
    target_bytes = _image_bytes(target_path, label=f"{example_id}/target_image")
    with Image.open(io.BytesIO(image_bytes)) as opened:
        d4_hash = normalized_d4_sha256(opened)
    source_d4 = record.get("normalized_d4_mask_sha256")
    if source_d4 and d4_hash != source_d4:
        raise ReleaseError(
            f"{example_id}: normalized D4 witness changed ({source_d4} != {d4_hash})"
        )

    grammar_id = str(record.get("grammar_id") or example_id)
    leakage_group_id = str(record.get("leakage_group_id") or grammar_id)
    footprint_raw = record.get("footprint_um")
    if not isinstance(footprint_raw, list):
        footprint_sidecar = _sidecar(card_dir, "footprint.json") or {}
        footprint_raw = footprint_sidecar.get("footprint_um", [])
    footprint = [float(value) for value in footprint_raw]
    if len(footprint) != 2 or any(value <= 0 for value in footprint):
        raise ReleaseError(f"{example_id}: invalid footprint {footprint}")

    metadata = _row_metadata(record, card_dir)
    parameters = _parameters(card_dir, code)
    if level == "l4":
        _validate_l4_source_port_evidence(
            example_id,
            _sidecar(card_dir, "topology_contract.json"),
        )
    topology = _topology(record, card_dir)
    observed_primitives = primitive_calls(code)
    prerequisites = _prerequisites(record)
    if level == "l1":
        prerequisites.extend(
            L0_PRIMITIVE_PREREQUISITES[primitive]
            for primitive in observed_primitives
            if primitive in L0_PRIMITIVE_PREREQUISITES
        )
        prerequisites = list(dict.fromkeys(prerequisites))
    for label, value in (
        ("metadata", metadata),
        ("parameters", parameters),
        ("topology", topology),
    ):
        no_absolute_path(value, label=f"{example_id}/{label}")

    label = _label(level, record)
    family = _family(level, record)
    instruction = _instruction(card_dir, footprint)
    row = {
        "schema_version": SCHEMA_VERSION,
        "id": example_id,
        "level": level.upper(),
        "curriculum_order": order,
        "image": {"bytes": image_bytes, "path": f"{example_id}.png"},
        "target_image": {
            "bytes": target_bytes,
            "path": f"{example_id}.target.png",
        },
        "code": code,
        "code_language": "python",
        "instruction": instruction,
        "label": label,
        "family": family,
        "concept_id": _concept_id(level, record),
        "representation_id": grammar_id,
        "grammar_id": grammar_id,
        "leakage_group_id": leakage_group_id,
        "variation_role": _public_variation_role(record),
        "primitive_calls": observed_primitives,
        "prerequisite_ids": prerequisites,
        "port_signature_json": canonical_json(
            record.get("port_evidence") or record.get("port_signature") or {}
        ),
        "footprint_um": footprint,
        "parameters_json": canonical_json(parameters),
        "topology_json": canonical_json(topology),
        "metadata_json": canonical_json(metadata),
        "image_sha256": sha256_bytes(image_bytes),
        "target_image_sha256": sha256_bytes(target_bytes),
        "code_sha256": sha256_bytes(code.encode("utf-8")),
        "normalized_d4_sha256": d4_hash,
        "view_policy": str(record.get("view_policy") or "max_visible_v1"),
        "source_dataset_digest_sha256": str(
            manifest.get("dataset_digest_sha256") or ""
        ),
        "source_generator_version": str(
            manifest.get("generator_version") or record.get("generator_version") or ""
        ),
    }
    if tuple(row) != ROW_COLUMNS:
        raise AssertionError("release row column order drifted")
    row_hits = scan_value_strings(example_id, row)
    if row_hits:
        raise ReleaseError("; ".join(row_hits))
    return row


def _source_summary(
    level: str,
    manifest: dict[str, Any],
    audit: dict[str, Any],
    row_count: int,
) -> dict[str, Any]:
    safe_manifest_keys = (
        "schema_version",
        "level",
        "status",
        "dataset_id",
        "dataset_schema",
        "dataset_digest_sha256",
        "generator_source_sha256",
        "generator_version",
        "selection_policy",
        "view_policy",
        "candidate_count",
        "public_task_count",
        "public_card_count",
        "identity_count",
        "primitive_count",
        "operation_count",
        "composition_count",
        "semantic_grammar_count",
        "family_counts",
        "role_counts",
        "public_role_counts",
        "duplicate_telemetry",
        "duplicate_gate",
        "lower_level_collision_gate",
    )
    summary = {
        "level": level.upper(),
        "exported_row_count": row_count,
        "manifest": _clean_metadata(
            {key: manifest[key] for key in safe_manifest_keys if key in manifest}
        ),
        "audit": _clean_metadata(audit),
    }
    no_absolute_path(summary, label=f"{level}/source_summary")
    return summary


def _extract_level(
    source_root: Path,
    output_root: Path,
    level: str,
    bank_name: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    bank = source_root / "rl" / "tasks" / bank_name
    manifest_path = bank / "manifest.json"
    audit_path = bank / "audit_report.json"
    if not manifest_path.is_file() or not audit_path.is_file():
        raise ReleaseError(f"{level}: incomplete source bank at {bank}")
    manifest = read_json(manifest_path)
    audit = read_json(audit_path)
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        raise ReleaseError(f"{level}: manifest has no records")
    if "accepted_only" not in str(manifest.get("status", "")):
        raise ReleaseError(f"{level}: source manifest is not accepted-only")
    if audit.get("accepted_only") is False or manifest.get("accepted_only") is False:
        raise ReleaseError(f"{level}: source bank contains non-accepted rows")
    if audit.get("passed") is False:
        raise ReleaseError(f"{level}: source audit did not pass")
    if audit.get("dataset_digest_sha256") != manifest.get("dataset_digest_sha256"):
        raise ReleaseError(f"{level}: source manifest/audit digest mismatch")
    for key in (
        "all_tasks_compiled",
        "all_tasks_pure",
        "all_tasks_conductor_verified",
        "all_views_deterministic",
    ):
        if key in manifest and manifest[key] is not True:
            raise ReleaseError(f"{level}: source gate is false: {key}")
    for key in (
        "compiled",
        "purity_clean",
        "conductor_reexecuted",
        "exact_views_verified",
        "reexecuted_card_count",
    ):
        if key in audit and audit[key] != len(records):
            raise ReleaseError(
                f"{level}: source audit count {key}={audit[key]} "
                f"does not match {len(records)} rows"
            )
    rows = [
        _build_row(
            level=level,
            order=order,
            bank=bank,
            manifest=manifest,
            record=record,
        )
        for order, record in enumerate(records)
    ]
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        duplicates = [item for item, count in Counter(ids).items() if count > 1]
        raise ReleaseError(f"{level}: duplicate ids: {duplicates}")

    source_summary = _source_summary(level, manifest, audit, len(rows))
    write_json(
        output_root / "metadata" / "source_reports" / f"{level}.json",
        source_summary,
    )
    return rows, source_summary


def _normalize_leakage_groups(rows: list[dict[str, Any]]) -> None:
    """Close source leakage groups over exact image aliases.

    Some deliberately retained L0 cross-API aliases have different source
    grammar IDs despite identical rasters.  A public split boundary must keep
    those aliases together.
    """

    parent = list(range(len(rows)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    by_source_group: dict[str, int] = {}
    by_exact_image: dict[str, int] = {}
    for index, row in enumerate(rows):
        for mapping, key in (
            (by_source_group, row["leakage_group_id"]),
            (by_exact_image, row["image_sha256"]),
        ):
            previous = mapping.setdefault(key, index)
            union(index, previous)

    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(rows)):
        groups[find(index)].append(index)
    for members in groups.values():
        ids = sorted(rows[index]["id"] for index in members)
        public_id = f"lg_{canonical_sha256(ids)[:20]}"
        for index in members:
            rows[index]["leakage_group_id"] = public_id


def _write_parquet(output_root: Path, level: str, rows: list[dict[str, Any]]) -> None:
    dataset = Dataset.from_list(rows, features=release_features())
    shard = output_root / "data" / level / "train-00000-of-00001.parquet"
    shard.parent.mkdir(parents=True, exist_ok=True)
    dataset.to_parquet(
        str(shard),
        batch_size=100,
    )


def _collision_report(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exact_groups: dict[str, list[str]] = defaultdict(list)
    d4_groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        exact_groups[row["image_sha256"]].append(row["id"])
        d4_groups[row["normalized_d4_sha256"]].append(row["id"])
    exact = sorted(sorted(group) for group in exact_groups.values() if len(group) > 1)
    d4 = sorted(sorted(group) for group in d4_groups.values() if len(group) > 1)
    return {
        "exact_duplicate_group_count": len(exact),
        "exact_duplicate_groups": exact,
        "d4_equivalent_group_count": len(d4),
        "d4_equivalent_groups": d4,
        "policy": (
            "Exact and D4-equivalent groups are reported rather than silently "
            "removed; leakage_group_id is the split boundary. L0 retains "
            "explicitly declared cross-API aliases and pose/calibration examples."
        ),
    }


def _promote_generated_release(stage_root: Path, output_root: Path) -> None:
    """Replace generated directories transactionally, restoring on failure."""

    generated_names = ("data", "metadata", "galleries")
    for name in generated_names:
        if not (stage_root / name).is_dir():
            raise ReleaseError(f"staged release is missing {name}/")
    backup_root = Path(
        tempfile.mkdtemp(
            prefix=f".{output_root.name}.backup.",
            dir=output_root.parent,
        )
    )
    moved_old: list[str] = []
    moved_new: list[str] = []
    try:
        for name in generated_names:
            destination = output_root / name
            if destination.exists():
                if not destination.is_dir():
                    raise ReleaseError(
                        f"generated destination is not a directory: {destination}"
                    )
                os.replace(destination, backup_root / name)
                moved_old.append(name)
        for name in generated_names:
            os.replace(stage_root / name, output_root / name)
            moved_new.append(name)
        write_checksums(output_root)
    except Exception:
        for name in reversed(moved_new):
            destination = output_root / name
            if destination.is_dir():
                shutil.rmtree(destination)
        for name in reversed(moved_old):
            os.replace(backup_root / name, output_root / name)
        raise
    finally:
        shutil.rmtree(backup_root, ignore_errors=True)


def build_release(
    source_root: Path,
    output_root: Path,
    *,
    bank_names: dict[str, str] | None = None,
    expected_release_digest: str | None = None,
    expected_row_count: int | None = None,
) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    output_root = _safe_generated_root(output_root)
    names = {**BANK_NAMES, **(bank_names or {})}
    if not (source_root / "rl" / "tasks").is_dir():
        raise ReleaseError(f"source root has no rl/tasks: {source_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    stage_root = Path(
        tempfile.mkdtemp(
            prefix=f".{output_root.name}.stage.",
            dir=output_root.parent,
        )
    )
    try:
        disable_progress_bar()
        all_rows: list[dict[str, Any]] = []
        rows_by_level: dict[str, list[dict[str, Any]]] = {}
        level_summaries: dict[str, Any] = {}
        for level in LEVELS:
            rows, source_summary = _extract_level(
                source_root,
                stage_root,
                level,
                names[level],
            )
            all_rows.extend(rows)
            rows_by_level[level] = rows
            level_summaries[level] = {
                "row_count": len(rows),
                "family_counts": dict(
                    sorted(Counter(row["family"] for row in rows).items())
                ),
                "variation_role_counts": dict(
                    sorted(Counter(row["variation_role"] for row in rows).items())
                ),
                "source_dataset_digest_sha256": rows[0]["source_dataset_digest_sha256"],
                "source_generator_version": rows[0]["source_generator_version"],
                "source_report_sha256": canonical_sha256(source_summary),
            }

        all_ids = [row["id"] for row in all_rows]
        if len(all_ids) != len(set(all_ids)):
            raise ReleaseError("example ids collide across curriculum levels")
        for curriculum_order, row in enumerate(all_rows):
            row["curriculum_order"] = curriculum_order
        _normalize_leakage_groups(all_rows)
        for level in LEVELS:
            _write_parquet(stage_root, level, rows_by_level[level])
        collision_report = _collision_report(all_rows)
        release_digest_records = [release_digest_record(row) for row in all_rows]
        release_digest = canonical_sha256(release_digest_records)
        catalog = {
            "schema_version": SCHEMA_VERSION,
            "release_digest_sha256": release_digest,
            "accepted_only": True,
            "canonical_format": "Parquet with embedded PNG bytes",
            "columns": list(ROW_COLUMNS),
            "configurations": ["all", "core-v1", *LEVELS],
            "levels": level_summaries,
            "total_rows": len(all_rows),
            "total_representation_ids": len(
                {row["representation_id"] for row in all_rows}
            ),
            "collision_report": collision_report,
        }
        write_json(stage_root / "metadata" / "catalog.json", catalog)
        gallery_records = render_release_galleries(stage_root)
        audit = {
            "schema_version": SCHEMA_VERSION,
            "release_digest_sha256": release_digest,
            "accepted_only": True,
            "level_count": len(LEVELS),
            "row_count": len(all_rows),
            "unique_id_count": len(set(all_ids)),
            "compiled_program_count": len(all_rows),
            "purity_clean_program_count": len(all_rows),
            "embedded_model_image_count": len(all_rows),
            "embedded_target_image_count": len(all_rows),
            "source_d4_witness_match_count": len(all_rows),
            "absolute_path_or_secret_hits": [],
            "collision_report": collision_report,
            "galleries": gallery_records,
            "gates": {
                "all_rows_from_accepted_source_records": True,
                "all_programs_compile": True,
                "all_programs_pass_purity": True,
                "all_images_decode_and_are_nonblank": True,
                "all_images_are_embedded": True,
                "all_source_d4_witnesses_match": True,
                "all_paths_are_release_relative": True,
            },
        }
        write_json(stage_root / "metadata" / "audit_report.json", audit)
        if (
            expected_release_digest is not None
            and release_digest != expected_release_digest
        ):
            raise ReleaseError(
                "staged release digest differs from the required freeze: "
                f"{release_digest} != {expected_release_digest}"
            )
        if expected_row_count is not None and len(all_rows) != expected_row_count:
            raise ReleaseError(
                "staged release row count differs from the required freeze: "
                f"{len(all_rows)} != {expected_row_count}"
            )
        _promote_generated_release(stage_root, output_root)
        return catalog
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def _parse_bank_override(values: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ReleaseError(f"bank override must be LEVEL=NAME: {value}")
        level, name = value.split("=", 1)
        level = level.lower()
        if level not in LEVELS or not name or "/" in name:
            raise ReleaseError(f"invalid bank override: {value}")
        overrides[level] = name
    return overrides


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="PixCell working tree containing audited rl/tasks banks.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Release package root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--bank",
        action="append",
        default=[],
        metavar="LEVEL=NAME",
        help="Override one source bank directory name.",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    catalog = build_release(
        args.source,
        args.output,
        bank_names=_parse_bank_override(args.bank),
    )
    print(
        f"built {catalog['total_rows']} rows; "
        f"release digest {catalog['release_digest_sha256']}"
    )


if __name__ == "__main__":
    main()
