#!/usr/bin/env python3
"""Validate a generic PixCell Hugging Face package against frozen sources."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
import yaml
from PIL import Image

from release.huggingface.build_release import (
    CALIBRATION_COLUMNS,
    CORE_ROW_COUNT,
    CORE_SOURCE_COLUMNS,
    EXPECTED_SPLIT_ROWS,
    FORBIDDEN_MODEL_COLUMNS,
    MANIFEST_SCHEMA_VERSION,
    MAX_ROWS_PER_SHARD,
    MODEL_COLUMNS,
    REFERENCE_COLUMNS,
    RELEASE_SCHEMA_VERSION,
    SOURCE_CORE_DIGEST,
    SOURCE_DEPTH_DIGEST,
    assert_frozen_sources,
    core_source_paths,
    depth_source_paths,
    sha256_file,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_CONFIG_SPLITS = {
    "depth": {"train": 3468, "validation": 1092},
    "core": {"train": 738},
    "references": {"train": 3468, "validation": 1092},
}
EXPECTED_CONFIG_PATHS = {
    "depth": {
        "train": "depth/data/train-*.parquet",
        "validation": "depth/data/validation-*.parquet",
    },
    "core": {"train": "core/data/train-*.parquet"},
    "references": {
        "train": "references/data/train-*.parquet",
        "validation": "references/data/validation-*.parquet",
    },
}
MODEL_CONFIGS = ("depth", "core")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SHA40 = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_SUPPORT_FILES = frozenset(
    {
        ".gitattributes",
        "README.md",
        "LICENSE",
        "CITATION.cff",
        "THIRD_PARTY_NOTICES.md",
        "assets/core.png",
        "assets/depth.png",
    }
)
EXPECTED_IDENTITY = {
    "algorithm": "sha256(source_id)[:20]",
    "depth_reference_join": "opaque_id",
    "core_is_ordered_depth_train_subset": True,
}


class ReleaseValidationError(RuntimeError):
    """Raised when a generated release differs from its declared contract."""


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _logical_digest(
    rows: Sequence[Mapping[str, Any]],
    *,
    payload_columns: frozenset[str],
) -> str:
    logical = [
        {key: value for key, value in row.items() if key not in payload_columns} for row in rows
    ]
    return hashlib.sha256(_canonical_json(logical).encode("utf-8")).hexdigest()


def _embedded_bytes(value: Any, *, field: str) -> bytes:
    if not isinstance(value, Mapping):
        raise ReleaseValidationError(f"{field} is not an embedded image mapping")
    payload = value.get("bytes")
    if not isinstance(payload, bytes) or not payload:
        raise ReleaseValidationError(f"{field} has no embedded image bytes")
    return payload


def _opaque_id(source_id: str) -> str:
    return hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:20]


def _embedded_image(value: Any, *, field: str) -> dict[str, Any]:
    return {"bytes": _embedded_bytes(value, field=field), "path": None}


def _footprint(value: Any) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ReleaseValidationError("source footprint_um must have two values")
    footprint = [float(item) for item in value]
    if any(not math.isfinite(item) or item <= 0 for item in footprint):
        raise ReleaseValidationError("source footprint_um values must be finite and positive")
    return footprint


def _calibration_from_target(
    target_image: Any,
    footprint_um: Any,
) -> dict[str, Any]:
    payload = _embedded_bytes(target_image, field="target_image")
    footprint = _footprint(footprint_um)
    try:
        image = Image.open(io.BytesIO(payload)).convert("L")
        image.load()
    except Exception as exc:
        raise ReleaseValidationError("target_image is not readable") from exc
    array = np.asarray(image)
    material = array < 245
    if not material.any():
        raise ReleaseValidationError("target_image contains no material")
    ys, xs = np.where(material)
    bbox = [
        int(xs.min()),
        int(ys.min()),
        int(xs.max()) + 1,
        int(ys.max()) + 1,
    ]
    bbox_size = [bbox[2] - bbox[0], bbox[3] - bbox[1]]
    return {
        "bbox": bbox,
        "bbox_size_px": bbox_size,
        "footprint_um": footprint,
        "image_size_px": [image.width, image.height],
        "offset": bbox[:2],
        "scale_px_per_um": [
            bbox_size[0] / footprint[0],
            bbox_size[1] / footprint[1],
        ],
        "white_threshold": 245,
    }


def _expected_calibration(row: Mapping[str, Any]) -> dict[str, Any]:
    try:
        metadata = json.loads(str(row["metadata_json"]))
    except json.JSONDecodeError as exc:
        raise ReleaseValidationError("source metadata_json is invalid") from exc
    if not isinstance(metadata, Mapping):
        raise ReleaseValidationError("source metadata_json is not an object")
    stored = metadata.get("calibration")
    if not isinstance(stored, Mapping):
        return _calibration_from_target(
            row["target_image"],
            row["footprint_um"],
        )
    if set(CALIBRATION_COLUMNS) - set(stored):
        raise ReleaseValidationError("source calibration fields are incomplete")
    return {key: stored[key] for key in CALIBRATION_COLUMNS}


def _expected_model_row(
    row: Mapping[str, Any],
    *,
    core_source_ids: frozenset[str],
) -> dict[str, Any]:
    expected = {
        "schema_version": "pixcell-model-row-v2",
        "opaque_id": _opaque_id(str(row["id"])),
        "image": _embedded_image(row["image"], field="image"),
        "footprint_um": _footprint(row["footprint_um"]),
        "code": str(row["code"]),
        "image_sha256": str(row["image_sha256"]),
        "code_sha256": str(row["code_sha256"]),
        "level": str(row["level"]),
        "curriculum_order": int(row["curriculum_order"]),
        "representation_id": str(row["representation_id"]),
        "leakage_group_id": str(row["leakage_group_id"]),
        "variation_role": str(row["variation_role"]),
        "realization_slot": int(row["realization_slot"]),
        "is_core": str(row["id"]) in core_source_ids,
    }
    if tuple(expected) != MODEL_COLUMNS:
        raise ReleaseValidationError("independent model schema differs")
    return expected


def _expected_reference_row(row: Mapping[str, Any]) -> dict[str, Any]:
    calibration = _expected_calibration(row)
    expected = {
        "schema_version": "pixcell-reference-row-v2",
        "opaque_id": _opaque_id(str(row["id"])),
        "target_image": _embedded_image(
            row["target_image"],
            field="target_image",
        ),
        "footprint_um": _footprint(row["footprint_um"]),
        "target_image_sha256": str(row["target_image_sha256"]),
        "primitive_calls": [str(item) for item in row["primitive_calls"]],
        "port_signature_json": str(row["port_signature_json"]),
        "topology_json": str(row["topology_json"]),
        "parameters_json": str(row["parameters_json"]),
        "family": str(row["family"]),
        "label": str(row["label"]),
        "view_policy": str(row["view_policy"]),
        "calibration_json": _canonical_json(calibration),
        "parent_opaque_id": _opaque_id(str(row["parent_core_id"])),
        "parent_code_sha256": str(row["parent_code_sha256"]),
        "parent_core_digest_sha256": str(row["parent_core_digest_sha256"]),
        "geometry_id": str(row["geometry_id"]),
        "realization_id": str(row["realization_id"]),
        "realization_slot": int(row["realization_slot"]),
        "transform_kind": str(row["transform_kind"]),
        "controlled_axes": [str(item) for item in row["controlled_axes"]],
        "parameter_delta_json": str(row["parameter_delta_json"]),
        "dependency_group": str(row["dependency_group"]),
        "split_role": str(row["split_role"]),
        "pose_id": str(row["pose_id"]),
        "render_id": str(row["render_id"]),
        "depth_generator_version": str(row["depth_generator_version"]),
        "logical_row_sha256": str(row["logical_row_sha256"]),
    }
    if tuple(expected) != REFERENCE_COLUMNS:
        raise ReleaseValidationError("independent reference schema differs")
    return expected


def _core_ordered_subset(
    core_rows: Sequence[Mapping[str, Any]],
    depth_train_rows: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    if len(core_rows) != CORE_ROW_COUNT:
        raise ReleaseValidationError(
            f"source core has {len(core_rows)} rows, expected {CORE_ROW_COUNT}"
        )
    core_ids = [str(row["id"]) for row in core_rows]
    if len(core_ids) != len(set(core_ids)):
        raise ReleaseValidationError("source core IDs are not unique")
    core_id_set = set(core_ids)
    selected = [row for row in depth_train_rows if str(row["id"]) in core_id_set]
    if [str(row["id"]) for row in selected] != core_ids:
        raise ReleaseValidationError("source core is not an ordered depth/train subset")
    for core, depth in zip(core_rows, selected, strict=True):
        for field in CORE_SOURCE_COLUMNS:
            if core[field] != depth[field]:
                raise ReleaseValidationError(
                    f"{core['id']}: source core/depth field differs: {field}"
                )
    return selected


def _assert_payload_hash(payload: bytes, expected: str, *, label: str) -> None:
    if not SHA256.fullmatch(expected):
        raise ReleaseValidationError(f"{label} has an invalid SHA-256 field")
    observed = hashlib.sha256(payload).hexdigest()
    if observed != expected:
        raise ReleaseValidationError(f"{label} payload SHA-256 is {observed}, expected {expected}")


def _load_rows(paths: Sequence[Path]) -> tuple[list[dict[str, Any]], tuple[str, ...]]:
    rows: list[dict[str, Any]] = []
    columns: tuple[str, ...] | None = None
    for path in paths:
        table = pq.read_table(path)
        observed = tuple(table.column_names)
        if columns is None:
            columns = observed
        elif observed != columns:
            raise ReleaseValidationError(
                f"Parquet column order differs in {path.relative_to(path.parent.parent)}"
            )
        rows.extend(table.to_pylist())
    if columns is None:
        raise ReleaseValidationError("no Parquet files were supplied")
    return rows, columns


def _projection_paths(
    release_root: Path,
    *,
    configuration: str,
    split: str,
) -> list[Path]:
    paths = sorted((release_root / configuration / "data").glob(f"{split}-*.parquet"))
    if not paths:
        raise ReleaseValidationError(f"no {configuration}/{split} Parquet shards in {release_root}")
    return paths


def _load_source_rows(paths: Sequence[Path]) -> list[dict[str, Any]]:
    rows, _ = _load_rows(paths)
    return rows


def _load_purity_checker(path: Path, *, module_name: str):
    spec = importlib.util.spec_from_file_location(
        module_name,
        path,
    )
    if spec is None or spec.loader is None:
        raise ReleaseValidationError(f"cannot import source policy from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "strict_purity_violations", module.purity_violations)


def _purity_checkers(dataset_root: Path) -> dict[str, Any]:
    repo_root = dataset_root.parent
    return {
        "frozen-admission": _load_purity_checker(
            dataset_root / "scripts" / "_shared.py",
            module_name="pixcell_frozen_dataset_shared",
        ),
        "canonical-runtime": _load_purity_checker(
            repo_root / "src" / "homi" / "conductor" / "source_policy.py",
            module_name="pixcell_canonical_source_policy",
        ),
    }


def _front_matter(card_path: Path) -> dict[str, Any]:
    text = card_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ReleaseValidationError("README.md has no YAML front matter")
    try:
        _, raw, _body = text.split("---\n", 2)
    except ValueError as exc:
        raise ReleaseValidationError("README.md front matter is not closed") from exc
    value = yaml.safe_load(raw)
    if not isinstance(value, dict):
        raise ReleaseValidationError("README.md front matter is not a mapping")
    return value


def _card_data_files(config: Mapping[str, Any]) -> dict[str, str]:
    records = config.get("data_files")
    if not isinstance(records, list):
        raise ReleaseValidationError("dataset config has no data_files list")
    result: dict[str, str] = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise ReleaseValidationError("dataset config has an invalid data_files row")
        split = str(record.get("split", ""))
        path = record.get("path")
        if not split or not isinstance(path, str):
            raise ReleaseValidationError("dataset config has an invalid split/path")
        result[split] = path
    return result


def _validate_card(card_path: Path) -> None:
    metadata = _front_matter(card_path)
    configs = metadata.get("configs")
    if not isinstance(configs, list):
        raise ReleaseValidationError("README.md has no configs list")
    by_name: dict[str, Mapping[str, Any]] = {}
    for config in configs:
        if not isinstance(config, Mapping):
            raise ReleaseValidationError("README.md contains an invalid config")
        name = str(config.get("config_name", ""))
        if not name or name in by_name:
            raise ReleaseValidationError("README.md has missing or duplicate configs")
        by_name[name] = config
    if set(by_name) != set(EXPECTED_CONFIG_SPLITS):
        raise ReleaseValidationError(
            f"README.md configs are {sorted(by_name)}, expected {sorted(EXPECTED_CONFIG_SPLITS)}"
        )
    defaults = [name for name, config in by_name.items() if config.get("default") is True]
    if defaults != ["depth"]:
        raise ReleaseValidationError(f"README.md defaults are {defaults}, expected ['depth']")
    for name, expected in EXPECTED_CONFIG_PATHS.items():
        observed = _card_data_files(by_name[name])
        if observed != expected:
            raise ReleaseValidationError(
                f"README.md {name} paths are {observed}, expected {expected}"
            )

    dataset_info = metadata.get("dataset_info")
    if not isinstance(dataset_info, list):
        raise ReleaseValidationError("README.md has no dataset_info list")
    observed_splits: dict[str, dict[str, int]] = {}
    for config in dataset_info:
        if not isinstance(config, Mapping):
            continue
        name = str(config.get("config_name", ""))
        records = config.get("splits")
        if not isinstance(records, list):
            continue
        observed_splits[name] = {
            str(record["name"]): int(record["num_examples"])
            for record in records
            if isinstance(record, Mapping) and "name" in record and "num_examples" in record
        }
    if observed_splits != EXPECTED_CONFIG_SPLITS:
        raise ReleaseValidationError(
            f"README.md split metadata is {observed_splits}, expected {EXPECTED_CONFIG_SPLITS}"
        )

    lowered = card_path.read_text(encoding="utf-8").lower()
    for forbidden in ("track-a-v1", "track-a-verifier-v1", "display note:"):
        if forbidden in lowered:
            raise ReleaseValidationError(
                f"README.md contains legacy Track A contract text: {forbidden}"
            )


def _assert_rows_equal(
    observed: Sequence[Mapping[str, Any]],
    expected: Sequence[Mapping[str, Any]],
    *,
    label: str,
) -> None:
    if len(observed) != len(expected):
        raise ReleaseValidationError(f"{label} has {len(observed)} rows, expected {len(expected)}")
    for index, (actual, wanted) in enumerate(zip(observed, expected, strict=True)):
        if actual != wanted:
            differing = [key for key in wanted if key not in actual or actual[key] != wanted[key]]
            raise ReleaseValidationError(f"{label} row {index} differs in fields {differing[:8]}")


def _validate_model_payloads(
    rows: Sequence[Mapping[str, Any]],
    *,
    purity_checkers: Mapping[str, Any],
    label: str,
) -> None:
    for index, row in enumerate(rows):
        key = str(row["opaque_id"])
        _assert_payload_hash(
            _embedded_bytes(row["image"], field="image"),
            str(row["image_sha256"]),
            label=f"{label}[{index}] {key} image",
        )
        code = str(row["code"])
        _assert_payload_hash(
            code.encode("utf-8"),
            str(row["code_sha256"]),
            label=f"{label}[{index}] {key} code",
        )
        for policy_name, purity_violations in purity_checkers.items():
            violations = purity_violations(code)
            if violations:
                raise ReleaseValidationError(
                    f"{label}[{index}] {key} violates {policy_name} source policy: {violations[0]}"
                )


def _validate_reference_payloads(
    rows: Sequence[Mapping[str, Any]],
    *,
    label: str,
) -> None:
    for index, row in enumerate(rows):
        key = str(row["opaque_id"])
        payload = _embedded_bytes(row["target_image"], field="target_image")
        _assert_payload_hash(
            payload,
            str(row["target_image_sha256"]),
            label=f"{label}[{index}] {key} target_image",
        )
        try:
            calibration = json.loads(str(row["calibration_json"]))
        except json.JSONDecodeError as exc:
            raise ReleaseValidationError(
                f"{label}[{index}] {key} has invalid calibration JSON"
            ) from exc
        if not isinstance(calibration, Mapping):
            raise ReleaseValidationError(f"{label}[{index}] {key} calibration is not an object")
        if set(calibration) != set(CALIBRATION_COLUMNS):
            raise ReleaseValidationError(f"{label}[{index}] {key} calibration fields differ")
        if calibration["footprint_um"] != row["footprint_um"]:
            raise ReleaseValidationError(f"{label}[{index}] {key} calibration footprint differs")
        bbox = calibration["bbox"]
        bbox_size = calibration["bbox_size_px"]
        image_size = calibration["image_size_px"]
        offset = calibration["offset"]
        if (
            not isinstance(bbox, list)
            or len(bbox) != 4
            or not isinstance(bbox_size, list)
            or len(bbox_size) != 2
            or not isinstance(image_size, list)
            or len(image_size) != 2
            or not isinstance(offset, list)
            or len(offset) != 2
        ):
            raise ReleaseValidationError(
                f"{label}[{index}] {key} calibration dimensions are invalid"
            )
        if bbox_size != [bbox[2] - bbox[0], bbox[3] - bbox[1]]:
            raise ReleaseValidationError(f"{label}[{index}] {key} calibration bbox size differs")
        if offset != bbox[:2]:
            raise ReleaseValidationError(f"{label}[{index}] {key} calibration offset differs")
        if calibration["white_threshold"] != 245:
            raise ReleaseValidationError(f"{label}[{index}] {key} calibration threshold differs")
        scale = calibration["scale_px_per_um"]
        if (
            not isinstance(scale, list)
            or len(scale) != 2
            or any(not math.isfinite(float(value)) or float(value) <= 0 for value in scale)
        ):
            raise ReleaseValidationError(f"{label}[{index}] {key} calibration scale is invalid")
        expected_scale = [
            bbox_size[0] / float(row["footprint_um"][0]),
            bbox_size[1] / float(row["footprint_um"][1]),
        ]
        if any(
            not math.isclose(
                float(actual),
                expected,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
            for actual, expected in zip(scale, expected_scale, strict=True)
        ):
            raise ReleaseValidationError(f"{label}[{index}] {key} calibration scale differs")
        derived = _calibration_from_target(
            row["target_image"],
            row["footprint_um"],
        )
        if image_size != derived["image_size_px"]:
            raise ReleaseValidationError(f"{label}[{index}] {key} calibration image size differs")
        boundary_delta = [
            abs(int(actual) - int(inferred))
            for actual, inferred in zip(
                bbox,
                derived["bbox"],
                strict=True,
            )
        ]
        if max(boundary_delta) > 1:
            raise ReleaseValidationError(
                f"{label}[{index}] {key} calibration bbox differs from raster"
            )
        for field in (
            "port_signature_json",
            "topology_json",
            "parameters_json",
            "parameter_delta_json",
        ):
            try:
                json.loads(str(row[field]))
            except json.JSONDecodeError as exc:
                raise ReleaseValidationError(f"{label}[{index}] {key} has invalid {field}") from exc


def _validate_manifest_files(
    release_root: Path,
    manifest: Mapping[str, Any],
) -> None:
    expected_shards: dict[str, tuple[str, str, int]] = {}
    for configuration, splits in EXPECTED_CONFIG_SPLITS.items():
        for split, row_count in splits.items():
            shard_count = math.ceil(row_count / MAX_ROWS_PER_SHARD)
            for index in range(shard_count):
                start = index * MAX_ROWS_PER_SHARD
                rows = min(MAX_ROWS_PER_SHARD, row_count - start)
                path = f"{configuration}/data/{split}-{index:05d}-of-{shard_count:05d}.parquet"
                expected_shards[path] = (configuration, split, rows)

    shards = manifest.get("shards")
    if not isinstance(shards, list):
        raise ReleaseValidationError("manifest has no shard list")
    shard_paths: set[str] = set()
    for record in shards:
        if not isinstance(record, Mapping):
            raise ReleaseValidationError("manifest has an invalid shard record")
        if set(record) != {
            "configuration",
            "split",
            "path",
            "rows",
            "sha256",
        }:
            raise ReleaseValidationError("manifest shard record fields differ from the contract")
        relative = str(record.get("path", ""))
        if not relative or relative in shard_paths:
            raise ReleaseValidationError("manifest has missing or duplicate shard paths")
        shard_paths.add(relative)
        if relative not in expected_shards:
            raise ReleaseValidationError(f"manifest has an unexpected shard path: {relative}")
        expected_configuration, expected_split, expected_rows = expected_shards[relative]
        if record.get("configuration") != expected_configuration:
            raise ReleaseValidationError(f"manifest shard configuration differs: {relative}")
        if record.get("split") != expected_split:
            raise ReleaseValidationError(f"manifest shard split differs: {relative}")
        if int(record.get("rows", -1)) != expected_rows:
            raise ReleaseValidationError(f"manifest shard plan row count differs: {relative}")
        declared_sha = str(record.get("sha256", ""))
        if not SHA256.fullmatch(declared_sha):
            raise ReleaseValidationError(f"manifest shard SHA-256 is invalid: {relative}")
        path = release_root / relative
        if not path.is_file():
            raise ReleaseValidationError(f"manifest shard is missing: {relative}")
        if sha256_file(path) != declared_sha:
            raise ReleaseValidationError(f"manifest shard hash differs: {relative}")
        rows = pq.read_metadata(path).num_rows
        if rows != expected_rows:
            raise ReleaseValidationError(f"manifest shard row count differs: {relative}")
        if rows < 1 or rows > MAX_ROWS_PER_SHARD:
            raise ReleaseValidationError(f"manifest shard size is invalid: {relative}")
    if shard_paths != set(expected_shards):
        raise ReleaseValidationError(
            "manifest shard plan differs: "
            f"missing={sorted(set(expected_shards) - shard_paths)}, "
            f"extra={sorted(shard_paths - set(expected_shards))}"
        )

    support = manifest.get("support_files")
    if not isinstance(support, Mapping):
        raise ReleaseValidationError("manifest has no support_files mapping")
    if set(support) != EXPECTED_SUPPORT_FILES:
        raise ReleaseValidationError(
            "manifest support-file inventory differs: "
            f"missing={sorted(EXPECTED_SUPPORT_FILES - set(support))}, "
            f"extra={sorted(set(support) - EXPECTED_SUPPORT_FILES)}"
        )
    for relative, expected in support.items():
        if not isinstance(expected, str) or not SHA256.fullmatch(expected):
            raise ReleaseValidationError(f"manifest support-file SHA-256 is invalid: {relative}")
        path = release_root / str(relative)
        if not path.is_file() or sha256_file(path) != expected:
            raise ReleaseValidationError(f"manifest support-file hash differs: {relative}")

    expected_files = shard_paths | EXPECTED_SUPPORT_FILES | {"manifest.json"}
    observed_files = {
        path.relative_to(release_root).as_posix()
        for path in release_root.rglob("*")
        if path.is_file()
    }
    if observed_files != expected_files:
        raise ReleaseValidationError(
            "release file set differs: "
            f"missing={sorted(expected_files - observed_files)}, "
            f"extra={sorted(observed_files - expected_files)}"
        )


def validate_release(*, release_root: Path, dataset_root: Path) -> dict[str, Any]:
    """Validate a complete generated Hub tree and return its bound digests."""

    release_root = release_root.expanduser().resolve()
    dataset_root = dataset_root.expanduser().resolve()
    assert_frozen_sources(dataset_root)
    manifest_path = release_root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseValidationError(f"cannot read release manifest: {exc}") from exc
    if not isinstance(manifest, Mapping):
        raise ReleaseValidationError("manifest is not a JSON object")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ReleaseValidationError("manifest schema version differs")
    if manifest.get("release_schema_version") != RELEASE_SCHEMA_VERSION:
        raise ReleaseValidationError("release schema version differs")
    if not SHA40.fullmatch(str(manifest.get("source_git_sha", ""))):
        raise ReleaseValidationError("manifest source Git SHA is invalid")
    if manifest.get("source") != {
        "core_logical_sha256": SOURCE_CORE_DIGEST,
        "depth_logical_sha256": SOURCE_DEPTH_DIGEST,
    }:
        raise ReleaseValidationError("manifest source digests differ")
    if manifest.get("identity") != EXPECTED_IDENTITY:
        raise ReleaseValidationError("manifest identity contract differs")
    if manifest.get("max_rows_per_shard") != MAX_ROWS_PER_SHARD:
        raise ReleaseValidationError("manifest shard limit differs")
    _validate_manifest_files(release_root, manifest)
    _validate_card(release_root / "README.md")

    core_source = _load_source_rows(core_source_paths(dataset_root))
    depth_source = {
        split: _load_source_rows(depth_source_paths(dataset_root, split))
        for split in EXPECTED_SPLIT_ROWS
    }
    core_depth_source = _core_ordered_subset(
        core_source,
        depth_source["train"],
    )
    core_source_ids = frozenset(str(row["id"]) for row in core_source)
    expected_depth = {
        split: [
            _expected_model_row(
                row,
                core_source_ids=core_source_ids,
            )
            for row in rows
        ]
        for split, rows in depth_source.items()
    }
    expected_core = [
        _expected_model_row(
            row,
            core_source_ids=core_source_ids,
        )
        for row in core_depth_source
    ]
    expected_references = {
        split: [_expected_reference_row(row) for row in rows]
        for split, rows in depth_source.items()
    }

    observed_depth: dict[str, list[dict[str, Any]]] = {}
    observed_references: dict[str, list[dict[str, Any]]] = {}
    for split, expected_rows in EXPECTED_SPLIT_ROWS.items():
        depth_rows, depth_columns = _load_rows(
            _projection_paths(
                release_root,
                configuration="depth",
                split=split,
            )
        )
        reference_rows, reference_columns = _load_rows(
            _projection_paths(
                release_root,
                configuration="references",
                split=split,
            )
        )
        if depth_columns != MODEL_COLUMNS:
            raise ReleaseValidationError(
                f"depth/{split} columns are {depth_columns}, expected {MODEL_COLUMNS}"
            )
        if set(depth_columns).intersection(FORBIDDEN_MODEL_COLUMNS):
            raise ReleaseValidationError(f"depth/{split} has verifier-only columns")
        if reference_columns != REFERENCE_COLUMNS:
            raise ReleaseValidationError(f"references/{split} columns differ from the schema")
        if len(depth_rows) != expected_rows or len(reference_rows) != expected_rows:
            raise ReleaseValidationError(f"{split} projected row counts differ")
        _assert_rows_equal(
            depth_rows,
            expected_depth[split],
            label=f"depth/{split}",
        )
        _assert_rows_equal(
            reference_rows,
            expected_references[split],
            label=f"references/{split}",
        )
        if [row["opaque_id"] for row in depth_rows] != [row["opaque_id"] for row in reference_rows]:
            raise ReleaseValidationError(f"{split} depth/reference join order differs")
        observed_depth[split] = depth_rows
        observed_references[split] = reference_rows

    core_rows, core_columns = _load_rows(
        _projection_paths(
            release_root,
            configuration="core",
            split="train",
        )
    )
    if core_columns != MODEL_COLUMNS:
        raise ReleaseValidationError("core/train columns differ from depth")
    _assert_rows_equal(core_rows, expected_core, label="core/train")
    if len(core_rows) != CORE_ROW_COUNT or not all(row["is_core"] for row in core_rows):
        raise ReleaseValidationError("core membership flags differ")
    if sum(bool(row["is_core"]) for row in observed_depth["train"]) != CORE_ROW_COUNT:
        raise ReleaseValidationError("depth/train core membership count differs")
    if any(row["is_core"] for row in observed_depth["validation"]):
        raise ReleaseValidationError("depth/validation contains core rows")
    core_ids = {str(row["opaque_id"]) for row in core_rows}
    if [row["opaque_id"] for row in core_rows] != [
        row["opaque_id"] for row in observed_depth["train"] if row["opaque_id"] in core_ids
    ]:
        raise ReleaseValidationError("core is not an ordered depth/train subset")

    all_ids = [
        str(row["opaque_id"]) for split in ("train", "validation") for row in observed_depth[split]
    ]
    if len(all_ids) != len(set(all_ids)):
        raise ReleaseValidationError("opaque IDs are not unique")
    source_ids = [
        str(row["id"]) for split in ("train", "validation") for row in depth_source[split]
    ]
    if all_ids != [_opaque_id(source_id) for source_id in source_ids]:
        raise ReleaseValidationError("opaque IDs do not match their source rows")

    purity_checkers = _purity_checkers(dataset_root)
    for split in ("train", "validation"):
        _validate_model_payloads(
            observed_depth[split],
            purity_checkers=purity_checkers,
            label=f"depth/{split}",
        )
        _validate_reference_payloads(
            observed_references[split],
            label=f"references/{split}",
        )

    configurations = manifest.get("configurations")
    if not isinstance(configurations, Mapping):
        raise ReleaseValidationError("manifest has no configurations mapping")
    if set(configurations) != set(EXPECTED_CONFIG_SPLITS):
        raise ReleaseValidationError("manifest configuration names differ")
    expected_for_digest = {
        "depth": observed_depth,
        "core": {"train": core_rows},
        "references": observed_references,
    }
    payloads = {
        "depth": frozenset({"image", "code"}),
        "core": frozenset({"image", "code"}),
        "references": frozenset({"target_image"}),
    }
    columns = {
        "depth": MODEL_COLUMNS,
        "core": MODEL_COLUMNS,
        "references": REFERENCE_COLUMNS,
    }
    for name, split_rows in EXPECTED_CONFIG_SPLITS.items():
        record = configurations[name]
        if not isinstance(record, Mapping):
            raise ReleaseValidationError(f"manifest {name} config is invalid")
        if record.get("columns") != list(columns[name]):
            raise ReleaseValidationError(f"manifest {name} columns differ")
        if record.get("split_rows") != split_rows:
            raise ReleaseValidationError(f"manifest {name} split rows differ")
        if bool(record.get("default")) != (name == "depth"):
            raise ReleaseValidationError(f"manifest {name} default flag differs")
        observed_digests = {
            split: _logical_digest(rows, payload_columns=payloads[name])
            for split, rows in expected_for_digest[name].items()
        }
        if record.get("logical_sha256") != observed_digests:
            raise ReleaseValidationError(f"manifest {name} logical digests differ")

    report = {
        "status": "pass",
        "source": {
            "core_logical_sha256": SOURCE_CORE_DIGEST,
            "depth_logical_sha256": SOURCE_DEPTH_DIGEST,
        },
        "configurations": EXPECTED_CONFIG_SPLITS,
        "opaque_ids": len(all_ids),
        "core_rows": len(core_rows),
        "source_policies": sorted(purity_checkers),
    }
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=REPO_ROOT / "dataset",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = validate_release(
        release_root=args.release_root,
        dataset_root=args.dataset_root,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
