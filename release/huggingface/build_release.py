#!/usr/bin/env python3
"""Build the generic PixCell Hugging Face release from frozen source releases.

The source Parquet files intentionally retain the complete frozen v1 schema.
This builder projects them into three reusable public configurations:

``depth``
    The default image-to-code corpus.
``core``
    The exact 738-row core curriculum, projected with the same schema.
``references``
    Separately keyed verifier inputs and descriptive lineage.

No prompt or training-recipe asset is part of this release.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from datasets import Dataset, Features, Image as HFImage, List as HFList, Value
from datasets.utils.logging import disable_progress_bar
import numpy as np
from PIL import Image


REPO_ROOT = Path(__file__).resolve().parents[2]

RELEASE_SCHEMA_VERSION = "pixcell-hf-release-v2"
MODEL_SCHEMA_VERSION = "pixcell-model-row-v2"
REFERENCE_SCHEMA_VERSION = "pixcell-reference-row-v2"
MANIFEST_SCHEMA_VERSION = "pixcell-hf-release-manifest-v2"

SOURCE_CORE_DIGEST = "e1c509dca337ce485efcb2b35101a052e06b12331b63a2f21a36c93b3682ea89"
SOURCE_DEPTH_DIGEST = "676c49134d4d044c7d84426cf8eeecf09302e74ca4aa548956f14b7631a4d80b"
CORE_ROW_COUNT = 738
EXPECTED_SPLIT_ROWS = {"train": 3468, "validation": 1092}
MAX_ROWS_PER_SHARD = 512
SHA40 = re.compile(r"^[0-9a-f]{40}$")

CORE_SOURCE_COLUMNS = (
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

MODEL_COLUMNS = (
    "schema_version",
    "opaque_id",
    "image",
    "footprint_um",
    "code",
    "image_sha256",
    "code_sha256",
    "level",
    "curriculum_order",
    "representation_id",
    "leakage_group_id",
    "variation_role",
    "realization_slot",
    "is_core",
)

REFERENCE_COLUMNS = (
    "schema_version",
    "opaque_id",
    "target_image",
    "footprint_um",
    "target_image_sha256",
    "primitive_calls",
    "port_signature_json",
    "topology_json",
    "parameters_json",
    "family",
    "label",
    "view_policy",
    "calibration_json",
    "parent_opaque_id",
    "parent_code_sha256",
    "parent_core_digest_sha256",
    "geometry_id",
    "realization_id",
    "realization_slot",
    "transform_kind",
    "controlled_axes",
    "parameter_delta_json",
    "dependency_group",
    "split_role",
    "pose_id",
    "render_id",
    "depth_generator_version",
    "logical_row_sha256",
)

CALIBRATION_COLUMNS = (
    "bbox",
    "bbox_size_px",
    "footprint_um",
    "image_size_px",
    "offset",
    "scale_px_per_um",
    "white_threshold",
)

FORBIDDEN_MODEL_COLUMNS = frozenset(
    {
        "instruction",
        "target_image",
        "target_image_sha256",
        "metadata_json",
        "parameters_json",
        "parameter_delta_json",
        "view_policy",
        "calibration_json",
        "verification_evidence_json",
        "primitive_calls",
        "port_signature_json",
        "topology_json",
    }
)


class ReleaseBuildError(RuntimeError):
    """Raised when a frozen source or projected release invariant fails."""


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def opaque_id(source_id: str) -> str:
    return hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:20]


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReleaseBuildError(f"{path} must contain a JSON object")
    return value


def _embedded_image(value: Any, *, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ReleaseBuildError(f"{field} must be an embedded image mapping")
    payload = value.get("bytes")
    if not isinstance(payload, bytes) or not payload:
        raise ReleaseBuildError(f"{field} must contain non-empty embedded bytes")
    return {"bytes": payload, "path": None}


def _footprint(value: Any) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ReleaseBuildError("footprint_um must contain two values")
    result = [float(item) for item in value]
    if any(not math.isfinite(item) or item <= 0 for item in result):
        raise ReleaseBuildError("footprint_um values must be finite and positive")
    return result


def _trimmed_calibration(
    metadata_json: str,
    *,
    target_image: Any,
    footprint_um: Any,
) -> str:
    try:
        metadata = json.loads(metadata_json)
    except json.JSONDecodeError as exc:
        raise ReleaseBuildError("metadata_json is not valid JSON") from exc
    if not isinstance(metadata, Mapping):
        raise ReleaseBuildError("metadata_json must contain an object")
    calibration = metadata.get("calibration")
    if isinstance(calibration, Mapping):
        missing = [key for key in CALIBRATION_COLUMNS if key not in calibration]
        if missing:
            raise ReleaseBuildError(f"calibration is missing fields: {missing}")
        trimmed = {key: calibration[key] for key in CALIBRATION_COLUMNS}
        return canonical_json(trimmed)

    embedded = _embedded_image(target_image, field="target_image")
    footprint = _footprint(footprint_um)
    try:
        image = Image.open(io.BytesIO(embedded["bytes"])).convert("L")
        image.load()
    except Exception as exc:
        raise ReleaseBuildError("target_image is not a readable image") from exc
    array = np.asarray(image)
    material = array < 245
    if not material.any():
        raise ReleaseBuildError("target_image contains no material")
    ys, xs = np.where(material)
    bbox = [
        int(xs.min()),
        int(ys.min()),
        int(xs.max()) + 1,
        int(ys.max()) + 1,
    ]
    bbox_size = [bbox[2] - bbox[0], bbox[3] - bbox[1]]
    trimmed = {
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
    return canonical_json(trimmed)


def model_features() -> Features:
    features = Features(
        {
            "schema_version": Value("string"),
            "opaque_id": Value("string"),
            "image": HFImage(decode=True),
            "footprint_um": HFList(Value("float64"), length=2),
            "code": Value("string"),
            "image_sha256": Value("string"),
            "code_sha256": Value("string"),
            "level": Value("string"),
            "curriculum_order": Value("int32"),
            "representation_id": Value("string"),
            "leakage_group_id": Value("string"),
            "variation_role": Value("string"),
            "realization_slot": Value("int32"),
            "is_core": Value("bool"),
        }
    )
    if tuple(features) != MODEL_COLUMNS:
        raise ReleaseBuildError("model feature order differs from MODEL_COLUMNS")
    return features


def reference_features() -> Features:
    features = Features(
        {
            "schema_version": Value("string"),
            "opaque_id": Value("string"),
            "target_image": HFImage(decode=True),
            "footprint_um": HFList(Value("float64"), length=2),
            "target_image_sha256": Value("string"),
            "primitive_calls": HFList(Value("string")),
            "port_signature_json": Value("string"),
            "topology_json": Value("string"),
            "parameters_json": Value("string"),
            "family": Value("string"),
            "label": Value("string"),
            "view_policy": Value("string"),
            "calibration_json": Value("string"),
            "parent_opaque_id": Value("string"),
            "parent_code_sha256": Value("string"),
            "parent_core_digest_sha256": Value("string"),
            "geometry_id": Value("string"),
            "realization_id": Value("string"),
            "realization_slot": Value("int32"),
            "transform_kind": Value("string"),
            "controlled_axes": HFList(Value("string")),
            "parameter_delta_json": Value("string"),
            "dependency_group": Value("string"),
            "split_role": Value("string"),
            "pose_id": Value("string"),
            "render_id": Value("string"),
            "depth_generator_version": Value("string"),
            "logical_row_sha256": Value("string"),
        }
    )
    if tuple(features) != REFERENCE_COLUMNS:
        raise ReleaseBuildError("reference feature order differs from REFERENCE_COLUMNS")
    return features


def project_model_row(row: Mapping[str, Any]) -> dict[str, Any]:
    slot = int(row["realization_slot"])
    projected = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "opaque_id": opaque_id(str(row["id"])),
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
        "realization_slot": slot,
        "is_core": slot in {-1, 0},
    }
    if tuple(projected) != MODEL_COLUMNS:
        raise ReleaseBuildError("projected model column order drift")
    if FORBIDDEN_MODEL_COLUMNS.intersection(projected):
        raise ReleaseBuildError("projected model row contains verifier-only fields")
    return projected


def project_reference_row(row: Mapping[str, Any]) -> dict[str, Any]:
    projected = {
        "schema_version": REFERENCE_SCHEMA_VERSION,
        "opaque_id": opaque_id(str(row["id"])),
        "target_image": _embedded_image(row["target_image"], field="target_image"),
        "footprint_um": _footprint(row["footprint_um"]),
        "target_image_sha256": str(row["target_image_sha256"]),
        "primitive_calls": [str(item) for item in row["primitive_calls"]],
        "port_signature_json": str(row["port_signature_json"]),
        "topology_json": str(row["topology_json"]),
        "parameters_json": str(row["parameters_json"]),
        "family": str(row["family"]),
        "label": str(row["label"]),
        "view_policy": str(row["view_policy"]),
        "calibration_json": _trimmed_calibration(
            str(row["metadata_json"]),
            target_image=row["target_image"],
            footprint_um=row["footprint_um"],
        ),
        "parent_opaque_id": opaque_id(str(row["parent_core_id"])),
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
    if tuple(projected) != REFERENCE_COLUMNS:
        raise ReleaseBuildError("projected reference column order drift")
    return projected


def core_source_paths(dataset_root: Path) -> list[Path]:
    paths = sorted((dataset_root / "data").glob("l*/train-*.parquet"))
    if len(paths) != 5:
        raise ReleaseBuildError(f"expected five core source shards, found {len(paths)}")
    return paths


def depth_source_paths(dataset_root: Path, split: str | None = None) -> list[Path]:
    pattern = f"{split}-*.parquet" if split else "*.parquet"
    paths = sorted((dataset_root / "depth-v1" / "data").glob(pattern))
    if not paths:
        raise ReleaseBuildError(f"no depth source shards for {split or 'all'}")
    return paths


def _assert_artifacts(
    *,
    release_root: Path,
    expected: Mapping[str, Any],
    prefix: str,
) -> None:
    expected_data = {
        str(relative): str(digest)
        for relative, digest in expected.items()
        if str(relative).startswith(prefix)
    }
    if not expected_data:
        raise ReleaseBuildError(f"freeze has no artifacts under {prefix}")
    for relative, digest in expected_data.items():
        path = release_root / relative
        if not path.is_file() or sha256_file(path) != digest:
            raise ReleaseBuildError(f"frozen source artifact differs: {path}")


def assert_frozen_sources(dataset_root: Path) -> None:
    core_freeze = _read_json(dataset_root / "factory" / "core-v1" / "freeze.json")
    if core_freeze.get("release_digest_sha256") != SOURCE_CORE_DIGEST:
        raise ReleaseBuildError("core logical digest differs from frozen source")
    if int(core_freeze.get("row_count", -1)) != CORE_ROW_COUNT:
        raise ReleaseBuildError("core row count differs from frozen source")
    core_artifacts = core_freeze.get("reference_artifacts")
    if not isinstance(core_artifacts, Mapping):
        raise ReleaseBuildError("core freeze has no reference_artifacts")
    _assert_artifacts(
        release_root=dataset_root,
        expected=core_artifacts,
        prefix="data/",
    )

    depth_root = dataset_root / "depth-v1"
    depth_freeze = _read_json(depth_root / "factory" / "freeze.json")
    if depth_freeze.get("logical_release_sha256") != SOURCE_DEPTH_DIGEST:
        raise ReleaseBuildError("depth logical digest differs from frozen source")
    if depth_freeze.get("parent_core_digest_sha256") != SOURCE_CORE_DIGEST:
        raise ReleaseBuildError("depth release is not bound to the frozen core")
    if int(depth_freeze.get("row_count", -1)) != sum(EXPECTED_SPLIT_ROWS.values()):
        raise ReleaseBuildError("depth row count differs from frozen source")
    depth_artifacts = depth_freeze.get("reference_artifacts")
    if not isinstance(depth_artifacts, Mapping):
        raise ReleaseBuildError("depth freeze has no reference_artifacts")
    _assert_artifacts(
        release_root=depth_root,
        expected=depth_artifacts,
        prefix="data/",
    )


def _load_rows(paths: Sequence[Path]) -> list[dict[str, Any]]:
    import pyarrow.parquet as pq

    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(pq.read_table(path).to_pylist())
    return rows


def assert_core_ordered_subset(
    core_rows: Sequence[Mapping[str, Any]],
    depth_train_rows: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    if len(core_rows) != CORE_ROW_COUNT:
        raise ReleaseBuildError(f"expected {CORE_ROW_COUNT} core rows")
    core_ids = [str(row["id"]) for row in core_rows]
    if len(core_ids) != len(set(core_ids)):
        raise ReleaseBuildError("core source contains duplicate IDs")
    core_id_set = set(core_ids)
    selected = [row for row in depth_train_rows if str(row["id"]) in core_id_set]
    if [str(row["id"]) for row in selected] != core_ids:
        raise ReleaseBuildError("core is not an order-preserving depth/train subset")
    for core, depth in zip(core_rows, selected, strict=True):
        for field in CORE_SOURCE_COLUMNS:
            if core[field] != depth[field]:
                raise ReleaseBuildError(
                    f"{core['id']}: frozen core field differs in depth/train: {field}"
                )
    return selected


def shard_plan(row_count: int) -> list[tuple[int, int]]:
    if row_count < 1:
        raise ReleaseBuildError("cannot shard an empty split")
    return [
        (start, min(start + MAX_ROWS_PER_SHARD, row_count))
        for start in range(0, row_count, MAX_ROWS_PER_SHARD)
    ]


def _write_shards(
    *,
    output: Path,
    configuration: str,
    split: str,
    rows: Sequence[Mapping[str, Any]],
    features: Features,
) -> list[dict[str, Any]]:
    plan = shard_plan(len(rows))
    total = len(plan)
    records: list[dict[str, Any]] = []
    data_root = output / configuration / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    for index, (start, stop) in enumerate(plan):
        filename = f"{split}-{index:05d}-of-{total:05d}.parquet"
        path = data_root / filename
        Dataset.from_list(list(rows[start:stop]), features=features).to_parquet(str(path))
        records.append(
            {
                "configuration": configuration,
                "split": split,
                "path": path.relative_to(output).as_posix(),
                "rows": stop - start,
                "sha256": sha256_file(path),
            }
        )
    return records


def _logical_digest(
    rows: Sequence[Mapping[str, Any]],
    *,
    payload_columns: frozenset[str],
) -> str:
    logical = [
        {key: value for key, value in row.items() if key not in payload_columns} for row in rows
    ]
    return hashlib.sha256(canonical_json(logical).encode("utf-8")).hexdigest()


def _card() -> str:
    return Path(__file__).with_name("CARD.md").read_text(encoding="utf-8")


def _prepare_output(output: Path) -> None:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)


def _assert_output_outside_dataset(dataset_root: Path, output: Path) -> None:
    if output == dataset_root or output.is_relative_to(dataset_root):
        raise ReleaseBuildError(f"release output must be outside the frozen dataset root: {output}")


def _source_git_sha(dataset_root: Path) -> str:
    """Return the repository commit containing the canonical dataset tree."""

    def git_output(*args: str) -> str:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=dataset_root,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ReleaseBuildError(f"cannot inspect dataset Git provenance: {exc}") from exc
        return result.stdout.strip()

    repo_root = Path(git_output("rev-parse", "--show-toplevel")).resolve()
    expected_dataset_root = (repo_root / "dataset").resolve()
    if dataset_root != expected_dataset_root:
        raise ReleaseBuildError(
            "dataset root must be the canonical repository dataset directory: "
            f"expected {expected_dataset_root}, got {dataset_root}"
        )
    source_git_sha = git_output("rev-parse", "HEAD")
    if not SHA40.fullmatch(source_git_sha):
        raise ReleaseBuildError(f"Git HEAD is not a full commit SHA: {source_git_sha!r}")
    return source_git_sha


def _write_release_assets(dataset_root: Path, output: Path) -> None:
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        source = dataset_root / name
        if not source.is_file():
            raise ReleaseBuildError(f"release asset is missing: {source}")
        shutil.copy2(source, output / name)
    citation = Path(__file__).with_name("CITATION.cff")
    if not citation.is_file():
        raise ReleaseBuildError(f"release asset is missing: {citation}")
    shutil.copy2(citation, output / "CITATION.cff")

    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    gallery_sources = {
        "core.png": dataset_root / "galleries" / "all.png",
        "depth.png": dataset_root / "depth-v1" / "galleries" / "overview.png",
    }
    for name, source in gallery_sources.items():
        if not source.is_file():
            raise ReleaseBuildError(f"gallery asset is missing: {source}")
        shutil.copy2(source, assets / name)

    (output / ".gitattributes").write_text(
        "*.parquet filter=lfs diff=lfs merge=lfs -text\n"
        "*.png filter=lfs diff=lfs merge=lfs -text\n",
        encoding="utf-8",
    )


def build_release(*, dataset_root: Path, output: Path) -> dict[str, Any]:
    dataset_root = dataset_root.expanduser().resolve()
    output = output.expanduser().resolve()
    _assert_output_outside_dataset(dataset_root, output)
    source_git_sha = _source_git_sha(dataset_root)
    assert_frozen_sources(dataset_root)
    _prepare_output(output)
    _write_release_assets(dataset_root, output)
    disable_progress_bar()

    core_source_rows = _load_rows(core_source_paths(dataset_root))
    depth_train_source = _load_rows(depth_source_paths(dataset_root, "train"))
    depth_validation_source = _load_rows(depth_source_paths(dataset_root, "validation"))
    observed_split_rows = {
        "train": len(depth_train_source),
        "validation": len(depth_validation_source),
    }
    if observed_split_rows != EXPECTED_SPLIT_ROWS:
        raise ReleaseBuildError(f"depth split rows differ: {observed_split_rows}")
    core_depth_rows = assert_core_ordered_subset(
        core_source_rows,
        depth_train_source,
    )

    all_source = [*depth_train_source, *depth_validation_source]
    source_ids = [str(row["id"]) for row in all_source]
    projected_ids = [opaque_id(value) for value in source_ids]
    if len(source_ids) != len(set(source_ids)):
        raise ReleaseBuildError("depth source contains duplicate IDs")
    if len(projected_ids) != len(set(projected_ids)):
        raise ReleaseBuildError("opaque ID collision")

    depth = {
        "train": [project_model_row(row) for row in depth_train_source],
        "validation": [project_model_row(row) for row in depth_validation_source],
    }
    core = {"train": [project_model_row(row) for row in core_depth_rows]}
    references = {
        "train": [project_reference_row(row) for row in depth_train_source],
        "validation": [project_reference_row(row) for row in depth_validation_source],
    }

    for split in EXPECTED_SPLIT_ROWS:
        if [row["opaque_id"] for row in depth[split]] != [
            row["opaque_id"] for row in references[split]
        ]:
            raise ReleaseBuildError(f"{split}: depth/reference join order differs")
    core_opaque_ids = {item["opaque_id"] for item in core["train"]}
    if [row["opaque_id"] for row in core["train"]] != [
        row["opaque_id"] for row in depth["train"] if row["opaque_id"] in core_opaque_ids
    ]:
        raise ReleaseBuildError("projected core order differs from depth/train")

    shard_records: list[dict[str, Any]] = []
    model_schema = model_features()
    reference_schema = reference_features()
    for split, rows in depth.items():
        shard_records.extend(
            _write_shards(
                output=output,
                configuration="depth",
                split=split,
                rows=rows,
                features=model_schema,
            )
        )
    shard_records.extend(
        _write_shards(
            output=output,
            configuration="core",
            split="train",
            rows=core["train"],
            features=model_schema,
        )
    )
    for split, rows in references.items():
        shard_records.extend(
            _write_shards(
                output=output,
                configuration="references",
                split=split,
                rows=rows,
                features=reference_schema,
            )
        )

    card_path = output / "README.md"
    card_path.write_text(_card(), encoding="utf-8")
    support_files = (
        ".gitattributes",
        "README.md",
        "LICENSE",
        "CITATION.cff",
        "THIRD_PARTY_NOTICES.md",
        "assets/core.png",
        "assets/depth.png",
    )
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "release_schema_version": RELEASE_SCHEMA_VERSION,
        "source_git_sha": source_git_sha,
        "source": {
            "core_logical_sha256": SOURCE_CORE_DIGEST,
            "depth_logical_sha256": SOURCE_DEPTH_DIGEST,
        },
        "configurations": {
            "depth": {
                "default": True,
                "columns": list(MODEL_COLUMNS),
                "split_rows": EXPECTED_SPLIT_ROWS,
                "logical_sha256": {
                    split: _logical_digest(
                        rows,
                        payload_columns=frozenset({"image", "code"}),
                    )
                    for split, rows in depth.items()
                },
            },
            "core": {
                "default": False,
                "columns": list(MODEL_COLUMNS),
                "split_rows": {"train": CORE_ROW_COUNT},
                "logical_sha256": {
                    "train": _logical_digest(
                        core["train"],
                        payload_columns=frozenset({"image", "code"}),
                    )
                },
            },
            "references": {
                "default": False,
                "columns": list(REFERENCE_COLUMNS),
                "split_rows": EXPECTED_SPLIT_ROWS,
                "logical_sha256": {
                    split: _logical_digest(
                        rows,
                        payload_columns=frozenset({"target_image"}),
                    )
                    for split, rows in references.items()
                },
            },
        },
        "identity": {
            "algorithm": "sha256(source_id)[:20]",
            "depth_reference_join": "opaque_id",
            "core_is_ordered_depth_train_subset": True,
        },
        "max_rows_per_shard": MAX_ROWS_PER_SHARD,
        "shards": shard_records,
        "support_files": {relative: sha256_file(output / relative) for relative in support_files},
    }
    (output / "manifest.json").write_text(
        json.dumps(
            manifest,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return manifest


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=REPO_ROOT / "dataset",
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = build_release(
        dataset_root=args.dataset_root,
        output=args.output,
    )
    print(
        json.dumps(
            {name: value["split_rows"] for name, value in manifest["configurations"].items()},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
