"""Schema and deterministic release helpers for the PixCell depth-v1 package.

This module is self-contained: it does not import the parent dataset factory
and never writes outside the release root explicitly passed by its caller.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from datasets import Features, Image as HFImage, List as HFList, Value


CORE_SCHEMA_VERSION = "pixcell-image-code-curriculum-v1"
DEPTH_SCHEMA_VERSION = "pixcell-depth-row-v1"
MANIFEST_SCHEMA_VERSION = "pixcell-depth-manifest-v1"
FREEZE_SCHEMA_VERSION = "pixcell-depth-freeze-v1"
RELEASE_NAME = "depth-v1"
FROZEN_LOGICAL_RELEASE_SHA256 = (
    "676c49134d4d044c7d84426cf8eeecf09302e74ca4aa548956f14b7631a4d80b"
)

APPROVED_REPRESENTATION_COUNT = 547
GEOMETRY_STATE_COUNT = 8
CORE_ROW_COUNT = 738
CORE_EXTRA_ROW_COUNT = CORE_ROW_COUNT - APPROVED_REPRESENTATION_COUNT
ANCHOR_ONLY_PARENT_IDS = frozenset(
    {"l2_02_rotated_edge_aligned_cluster__s03__proposal_b"}
)
DEPTH_ELIGIBLE_COUNT = APPROVED_REPRESENTATION_COUNT - len(
    ANCHOR_ONLY_PARENT_IDS
)
DEPTH_DESCENDANT_COUNT = DEPTH_ELIGIBLE_COUNT * (GEOMETRY_STATE_COUNT - 1)
DEPTH_ROW_COUNT = CORE_ROW_COUNT + DEPTH_DESCENDANT_COUNT
TRAIN_ROW_COUNT = CORE_ROW_COUNT + DEPTH_ELIGIBLE_COUNT * 5
VALIDATION_ROW_COUNT = DEPTH_ELIGIBLE_COUNT * 2

CORE_ROW_COLUMNS = (
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

DEPTH_CONTROL_COLUMNS = (
    "depth_schema_version",
    "parent_core_id",
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
    "verification_evidence_json",
    "depth_generator_version",
    "logical_row_sha256",
)

DEPTH_ROW_COLUMNS = (*CORE_ROW_COLUMNS, *DEPTH_CONTROL_COLUMNS)
NON_LOGICAL_PAYLOAD_COLUMNS = frozenset(
    {"image", "target_image", "code", "logical_row_sha256"}
)
EXPECTED_STATE_IDS = tuple(f"r{slot:02d}" for slot in range(GEOMETRY_STATE_COUNT))
EXPECTED_SPLIT_COUNTS = {
    "train": TRAIN_ROW_COUNT,
    "validation": VALIDATION_ROW_COUNT,
}
HOST_CONTROL_FILES = frozenset({".gitattributes", ".gitignore", ".gitkeep"})
SAFE_SPLIT = re.compile(r"^[a-z][a-z0-9_-]*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PROHIBITED_EVIDENCE_KEY_PARTS = ("admission", "quarantine", "status")


class DepthSchemaError(RuntimeError):
    """Raised when a depth-v1 schema or release invariant is violated."""


@dataclass(frozen=True)
class ShardPlan:
    """One deterministic, half-open row interval for a split shard."""

    split: str
    index: int
    total: int
    start: int
    stop: int
    filename: str

    @property
    def row_count(self) -> int:
        return self.stop - self.start

    def to_dict(self) -> dict[str, Any]:
        return {
            "split": self.split,
            "index": self.index,
            "total": self.total,
            "start": self.start,
            "stop": self.stop,
            "row_count": self.row_count,
            "filename": self.filename,
        }


def canonical_json(value: Any) -> str:
    """Serialize JSON-compatible data with one stable byte representation."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: Any) -> None:
    """Write human-readable JSON while preserving canonical data semantics."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            value,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def depth_features() -> Features:
    """Return loader-free Hugging Face features for depth-v1 Parquet shards."""

    features: dict[str, Any] = {
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
        "depth_schema_version": Value("string"),
        "parent_core_id": Value("string"),
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
        "verification_evidence_json": Value("string"),
        "depth_generator_version": Value("string"),
        "logical_row_sha256": Value("string"),
    }
    if tuple(features) != DEPTH_ROW_COLUMNS:
        raise DepthSchemaError("Hugging Face feature order differs from depth schema")
    return Features(features)


def _require_complete_row(row: Mapping[str, Any]) -> None:
    missing = sorted(set(DEPTH_ROW_COLUMNS) - set(row))
    extra = sorted(set(row) - set(DEPTH_ROW_COLUMNS))
    if missing or extra:
        raise DepthSchemaError(
            f"depth row columns differ: missing={missing}, extra={extra}"
        )


def logical_row_record(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return the complete logical row, replacing large payloads by hashes."""

    _require_complete_row(row)
    if row["schema_version"] != CORE_SCHEMA_VERSION:
        raise DepthSchemaError("parent-compatible core row schema version drift")
    if row["depth_schema_version"] != DEPTH_SCHEMA_VERSION:
        raise DepthSchemaError("depth row schema version drift")
    return {
        column: row[column]
        for column in DEPTH_ROW_COLUMNS
        if column not in NON_LOGICAL_PAYLOAD_COLUMNS
    }


def logical_row_sha256(row: Mapping[str, Any]) -> str:
    return canonical_sha256(logical_row_record(row))


def bind_logical_row_sha256(row: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copied row with its non-circular logical digest populated."""

    result = dict(row)
    result["logical_row_sha256"] = logical_row_sha256(result)
    return result


def verify_logical_row_sha256(row: Mapping[str, Any]) -> None:
    _require_complete_row(row)
    expected = logical_row_sha256(row)
    if row["logical_row_sha256"] != expected:
        raise DepthSchemaError(f"{row.get('id', '<row>')}: logical row digest mismatch")


def logical_release_sha256(rows: Iterable[Mapping[str, Any]]) -> str:
    """Hash a release as a stable, ID-sorted collection of logical rows."""

    materialized = list(rows)
    ids = [str(row.get("id", "")) for row in materialized]
    if not ids or any(not value for value in ids):
        raise DepthSchemaError("logical release requires nonempty row IDs")
    if len(ids) != len(set(ids)):
        raise DepthSchemaError("logical release row IDs are not unique")
    ordered = sorted(materialized, key=lambda row: str(row["id"]))
    return canonical_sha256([logical_row_record(row) for row in ordered])


def shard_filename(split: str, index: int, total: int) -> str:
    """Return the standard deterministic Hugging Face Parquet shard name."""

    if SAFE_SPLIT.fullmatch(split) is None:
        raise DepthSchemaError(f"unsafe split name: {split!r}")
    if (
        isinstance(index, bool)
        or isinstance(total, bool)
        or not isinstance(index, int)
        or not isinstance(total, int)
        or total < 1
        or total > 99999
        or index < 0
        or index >= total
    ):
        raise DepthSchemaError(f"invalid shard position {index} of {total}")
    return f"{split}-{index:05d}-of-{total:05d}.parquet"


def plan_shards(
    row_count: int,
    *,
    max_rows_per_shard: int,
    split: str,
) -> tuple[ShardPlan, ...]:
    """Partition an ordered split into deterministic contiguous shards."""

    if isinstance(row_count, bool) or not isinstance(row_count, int) or row_count < 1:
        raise DepthSchemaError("row_count must be a positive integer")
    if (
        isinstance(max_rows_per_shard, bool)
        or not isinstance(max_rows_per_shard, int)
        or max_rows_per_shard < 1
    ):
        raise DepthSchemaError("max_rows_per_shard must be a positive integer")
    total = math.ceil(row_count / max_rows_per_shard)
    return tuple(
        ShardPlan(
            split=split,
            index=index,
            total=total,
            start=index * max_rows_per_shard,
            stop=min(row_count, (index + 1) * max_rows_per_shard),
            filename=shard_filename(split, index, total),
        )
        for index in range(total)
    )


def _valid_sha256(value: object, *, label: str) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise DepthSchemaError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _json_object(value: object, *, label: str) -> dict[str, Any]:
    if not isinstance(value, str):
        raise DepthSchemaError(f"{label} must be JSON text")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise DepthSchemaError(f"{label} is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise DepthSchemaError(f"{label} must encode a JSON object")
    return parsed


def _verify_public_evidence(value: object, *, label: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in PROHIBITED_EVIDENCE_KEY_PARTS):
                raise DepthSchemaError(
                    f"{label} contains a non-public control key: {key!r}"
                )
            _verify_public_evidence(child, label=label)
    elif isinstance(value, list):
        for child in value:
            _verify_public_evidence(child, label=label)


def validate_depth_population(
    rows: Iterable[Mapping[str, Any]],
    *,
    expected_parent_core_digest_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate the complete depth-v1 population contract."""

    materialized = list(rows)
    if len(materialized) != DEPTH_ROW_COUNT:
        raise DepthSchemaError(
            f"depth-v1 row count {len(materialized)} != {DEPTH_ROW_COUNT}"
        )
    by_parent: dict[str, dict[int, Mapping[str, Any]]] = defaultdict(dict)
    dependency_by_parent: dict[str, str] = {}
    leakage_by_parent: dict[str, str] = {}
    code_by_parent: dict[str, str] = {}
    core_extra_count = 0
    core_extra_parent_ids: set[str] = set()
    split_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    geometry_ids: set[str] = set()
    row_ids: set[str] = set()
    parent_digests: set[str] = set()

    for row in materialized:
        _require_complete_row(row)
        verify_logical_row_sha256(row)
        row_id = str(row["id"])
        parent_id = str(row["parent_core_id"])
        if not row_id or row_id in row_ids or not parent_id:
            raise DepthSchemaError("depth row or parent IDs are empty or duplicated")
        row_ids.add(row_id)
        parent_digest = _valid_sha256(
            row["parent_core_digest_sha256"],
            label=f"{row_id}/parent_core_digest_sha256",
        )
        _valid_sha256(
            row["parent_code_sha256"],
            label=f"{row_id}/parent_code_sha256",
        )
        parent_digests.add(parent_digest)
        dependency = str(row["dependency_group"])
        if not dependency:
            raise DepthSchemaError(f"{row_id}: dependency_group is empty")
        previous_dependency = dependency_by_parent.setdefault(parent_id, dependency)
        if previous_dependency != dependency:
            raise DepthSchemaError(
                f"{parent_id}: dependency_group differs across descendants"
            )
        leakage_group = str(row["leakage_group_id"])
        if not leakage_group:
            raise DepthSchemaError(f"{row_id}: leakage_group_id is empty")
        previous_leakage = leakage_by_parent.setdefault(parent_id, leakage_group)
        if previous_leakage != leakage_group:
            raise DepthSchemaError(
                f"{parent_id}: leakage_group_id differs across descendants"
            )
        parent_code = str(row["parent_code_sha256"])
        previous_code = code_by_parent.setdefault(parent_id, parent_code)
        if previous_code != parent_code:
            raise DepthSchemaError(
                f"{parent_id}: parent_code_sha256 differs across descendants"
            )

        slot = row["realization_slot"]
        if isinstance(slot, bool) or not isinstance(slot, int):
            raise DepthSchemaError(f"{row_id}: realization_slot is not an integer")
        controlled_axes = row["controlled_axes"]
        if (
            not isinstance(controlled_axes, list)
            or any(not isinstance(axis, str) or not axis for axis in controlled_axes)
            or len(controlled_axes) != len(set(controlled_axes))
        ):
            raise DepthSchemaError(
                f"{row_id}: controlled_axes must contain unique nonempty strings"
            )
        _json_object(
            row["parameter_delta_json"],
            label=f"{row_id}/parameter_delta_json",
        )
        verification_evidence = _json_object(
            row["verification_evidence_json"],
            label=f"{row_id}/verification_evidence_json",
        )
        _verify_public_evidence(
            verification_evidence,
            label=f"{row_id}/verification_evidence_json",
        )
        for field in (
            "transform_kind",
            "dependency_group",
            "pose_id",
            "render_id",
            "depth_generator_version",
        ):
            if not isinstance(row[field], str) or not row[field]:
                raise DepthSchemaError(f"{row_id}: {field} must be nonempty")
        role = str(row["split_role"])
        role_counts[role] += 1
        if slot == -1:
            if role != "core-extra":
                raise DepthSchemaError(
                    f"{row_id}: slot -1 must have split_role core-extra"
                )
            core_extra_count += 1
            core_extra_parent_ids.add(parent_id)
            split_counts["train"] += 1
            continue
        if not 0 <= slot < GEOMETRY_STATE_COUNT:
            raise DepthSchemaError(f"{row_id}: realization_slot is outside -1..7")
        if row["realization_id"] != EXPECTED_STATE_IDS[slot]:
            raise DepthSchemaError(
                f"{row_id}: realization_id does not match slot {slot}"
            )
        expected_role = "train" if slot <= 5 else "validation"
        if role != expected_role:
            raise DepthSchemaError(
                f"{row_id}: slot {slot} must have split_role {expected_role}"
            )
        if slot in by_parent[parent_id]:
            raise DepthSchemaError(f"{parent_id}: repeated realization slot {slot}")
        if slot == 0:
            if row_id != parent_id:
                raise DepthSchemaError(
                    f"{row_id}: r00 anchor must bind itself as parent_core_id"
                )
            if row["parent_code_sha256"] != row["code_sha256"]:
                raise DepthSchemaError(
                    f"{row_id}: r00 parent code hash differs from anchor code"
                )
        by_parent[parent_id][slot] = row
        geometry_id = str(row["geometry_id"])
        if not geometry_id or geometry_id in geometry_ids:
            raise DepthSchemaError("geometry_id values must be nonempty and unique")
        geometry_ids.add(geometry_id)
        split_counts[expected_role] += 1

    if expected_parent_core_digest_sha256 is not None:
        _valid_sha256(
            expected_parent_core_digest_sha256,
            label="expected parent core digest",
        )
        if parent_digests != {expected_parent_core_digest_sha256}:
            raise DepthSchemaError("rows are not bound to the expected core digest")
    elif len(parent_digests) != 1:
        raise DepthSchemaError("depth rows bind to more than one core release")

    if len(by_parent) != APPROVED_REPRESENTATION_COUNT:
        raise DepthSchemaError(
            f"depth parent count {len(by_parent)} != {APPROVED_REPRESENTATION_COUNT}"
        )
    unknown_extra_parents = sorted(core_extra_parent_ids - set(by_parent))
    if unknown_extra_parents:
        raise DepthSchemaError(
            f"core extras bind to unknown semantic anchors: {unknown_extra_parents[:5]}"
        )
    expected_slots = set(range(GEOMETRY_STATE_COUNT))
    incomplete = sorted(
        parent_id
        for parent_id, states in by_parent.items()
        if set(states)
        != (
            {0}
            if parent_id in ANCHOR_ONLY_PARENT_IDS
            else expected_slots
        )
    )
    if incomplete:
        raise DepthSchemaError(
            "parents with realization slots outside their frozen schedule: "
            f"{incomplete[:5]}"
        )
    observed_anchor_only = {
        parent_id for parent_id, states in by_parent.items() if set(states) == {0}
    }
    if observed_anchor_only != set(ANCHOR_ONLY_PARENT_IDS):
        raise DepthSchemaError(
            "anchor-only parent inventory differs: "
            f"observed={sorted(observed_anchor_only)}, "
            f"expected={sorted(ANCHOR_ONLY_PARENT_IDS)}"
        )
    duplicate_inputs = sorted(
        parent_id
        for parent_id, states in by_parent.items()
        if len(
            {
                (
                    str(row["image_sha256"]),
                    str(row["instruction"]),
                )
                for row in states.values()
            }
        )
        != len(states)
    )
    if duplicate_inputs:
        raise DepthSchemaError(
            "parents with repeated model inputs: "
            f"{duplicate_inputs[:5]}"
        )
    if core_extra_count != CORE_EXTRA_ROW_COUNT:
        raise DepthSchemaError(
            f"core-extra row count {core_extra_count} != {CORE_EXTRA_ROW_COUNT}"
        )
    if dict(split_counts) != EXPECTED_SPLIT_COUNTS:
        raise DepthSchemaError(
            f"depth split counts {dict(split_counts)} != {EXPECTED_SPLIT_COUNTS}"
        )
    return {
        "row_count": len(materialized),
        "approved_representation_count": len(by_parent),
        "complete_depth_representation_count": DEPTH_ELIGIBLE_COUNT,
        "anchor_only_representation_count": len(ANCHOR_ONLY_PARENT_IDS),
        "anchor_only_parent_ids": sorted(ANCHOR_ONLY_PARENT_IDS),
        "geometry_state_count": GEOMETRY_STATE_COUNT,
        "geometry_row_count": len(geometry_ids),
        "core_extra_row_count": core_extra_count,
        "split_counts": dict(sorted(split_counts.items())),
        "split_role_counts": dict(sorted(role_counts.items())),
        "realization_counts": {
            state_id: (
                APPROVED_REPRESENTATION_COUNT
                if state_id == "r00"
                else DEPTH_ELIGIBLE_COUNT
            )
            for state_id in EXPECTED_STATE_IDS
        },
        "parent_core_digest_sha256": next(iter(parent_digests)),
    }


def _normalize_shard_records(
    shards: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    normalized = []
    seen_paths: set[str] = set()
    for raw in shards:
        split = str(raw.get("split", ""))
        index = raw.get("index")
        total = raw.get("total")
        rows = raw.get("rows")
        path = str(raw.get("path", ""))
        if (
            isinstance(index, bool)
            or not isinstance(index, int)
            or isinstance(total, bool)
            or not isinstance(total, int)
            or isinstance(rows, bool)
            or not isinstance(rows, int)
            or rows < 1
        ):
            raise DepthSchemaError("manifest shard positions/counts are malformed")
        expected_name = shard_filename(split, index, total)
        if Path(path).name != expected_name or Path(path).is_absolute():
            raise DepthSchemaError(f"non-deterministic shard path: {path!r}")
        if ".." in Path(path).parts or path in seen_paths:
            raise DepthSchemaError(f"unsafe or repeated shard path: {path!r}")
        seen_paths.add(path)
        digest = _valid_sha256(
            raw.get("sha256"),
            label=f"{path}/sha256",
        )
        size = raw.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 1:
            raise DepthSchemaError(f"{path}: shard byte size is invalid")
        normalized.append(
            {
                "split": split,
                "index": index,
                "total": total,
                "path": path,
                "rows": rows,
                "bytes": size,
                "sha256": digest,
            }
        )
    split_order = {"train": 0, "validation": 1}
    normalized.sort(
        key=lambda row: (
            split_order.get(str(row["split"]), 99),
            str(row["split"]),
            int(row["index"]),
        )
    )
    by_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in normalized:
        by_split[str(row["split"])].append(row)
    if set(by_split) != set(EXPECTED_SPLIT_COUNTS):
        raise DepthSchemaError("manifest shards must contain train and validation")
    for split, records in by_split.items():
        total = len(records)
        if any(
            record["total"] != total or record["index"] != index
            for index, record in enumerate(records)
        ):
            raise DepthSchemaError(f"{split}: shard sequence is not contiguous")
        observed_rows = sum(int(record["rows"]) for record in records)
        if observed_rows != EXPECTED_SPLIT_COUNTS[split]:
            raise DepthSchemaError(
                f"{split}: shard rows {observed_rows} != {EXPECTED_SPLIT_COUNTS[split]}"
            )
    return normalized


def build_manifest(
    rows: Iterable[Mapping[str, Any]],
    *,
    shards: Sequence[Mapping[str, Any]],
    depth_generator_version: str,
    expected_parent_core_digest_sha256: str | None = None,
) -> dict[str, Any]:
    """Build the deterministic public manifest from reviewed rows and shards."""

    materialized = list(rows)
    summary = validate_depth_population(
        materialized,
        expected_parent_core_digest_sha256=expected_parent_core_digest_sha256,
    )
    if not depth_generator_version:
        raise DepthSchemaError("depth_generator_version must be nonempty")
    versions = {str(row["depth_generator_version"]) for row in materialized}
    if versions != {depth_generator_version}:
        raise DepthSchemaError("row generator versions differ from manifest")
    normalized_shards = _normalize_shard_records(shards)
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "release_name": RELEASE_NAME,
        "depth_schema_version": DEPTH_SCHEMA_VERSION,
        "core_schema_version": CORE_SCHEMA_VERSION,
        "parent_core_digest_sha256": summary["parent_core_digest_sha256"],
        "depth_generator_version": depth_generator_version,
        "logical_row_order": "id_ascending",
        "logical_release_sha256": logical_release_sha256(materialized),
        **{
            key: value
            for key, value in summary.items()
            if key != "parent_core_digest_sha256"
        },
        "shards": normalized_shards,
    }


def _relative_path(root: Path, relative: str, *, label: str) -> Path:
    raw = Path(relative)
    if not relative or raw.is_absolute() or ".." in raw.parts:
        raise DepthSchemaError(f"{label} must be release-relative")
    path = (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise DepthSchemaError(f"{label} escapes the release root") from exc
    return path


def _relative_file(root: Path, relative: str, *, label: str) -> Path:
    path = _relative_path(root, relative, label=label)
    if not path.is_file():
        raise DepthSchemaError(f"{label} is missing: {relative}")
    return path


def build_freeze(
    release_root: Path,
    manifest: Mapping[str, Any],
    *,
    manifest_path: str,
    reference_paths: Sequence[str],
) -> dict[str, Any]:
    """Bind a completed manifest and selected release artifacts by hash."""

    root = release_root.expanduser().resolve()
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise DepthSchemaError("cannot freeze a non-depth-v1 manifest")
    manifest_file = _relative_file(root, manifest_path, label="manifest")
    try:
        recorded_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DepthSchemaError("manifest file is not valid UTF-8 JSON") from exc
    if recorded_manifest != dict(manifest):
        raise DepthSchemaError(
            "manifest object differs from the manifest file being frozen"
        )
    references: dict[str, str] = {}
    for relative in sorted(set(reference_paths)):
        path = _relative_file(root, relative, label=f"reference {relative}")
        references[relative] = sha256_file(path)
    return {
        "schema_version": FREEZE_SCHEMA_VERSION,
        "release_name": RELEASE_NAME,
        "depth_schema_version": DEPTH_SCHEMA_VERSION,
        "logical_release_sha256": manifest["logical_release_sha256"],
        "parent_core_digest_sha256": manifest["parent_core_digest_sha256"],
        "row_count": manifest["row_count"],
        "approved_representation_count": manifest["approved_representation_count"],
        "complete_depth_representation_count": manifest[
            "complete_depth_representation_count"
        ],
        "anchor_only_representation_count": manifest[
            "anchor_only_representation_count"
        ],
        "anchor_only_parent_ids": manifest["anchor_only_parent_ids"],
        "geometry_state_count": manifest["geometry_state_count"],
        "manifest": {
            "path": manifest_path,
            "sha256": sha256_file(manifest_file),
        },
        "reference_artifacts": references,
    }


def iter_release_files(root: Path) -> Iterable[Path]:
    """Yield checksum-bearing files in stable relative-path order."""

    resolved = root.expanduser().resolve()
    if not resolved.is_dir():
        raise DepthSchemaError(f"release root is not a directory: {resolved}")
    for path in sorted(resolved.rglob("*")):
        if path.is_symlink():
            raise DepthSchemaError(
                f"release contains a symbolic link: {path.relative_to(resolved)}"
            )
        if not path.is_file():
            continue
        if path.name == "checksums.sha256" or path.name in HOST_CONTROL_FILES:
            continue
        if any(
            part in {"__pycache__", ".pytest_cache", ".ruff_cache", ".git"}
            for part in path.parts
        ):
            continue
        yield path


def write_checksums(
    release_root: Path,
    *,
    relative_path: str = "metadata/checksums.sha256",
) -> Path:
    """Write a complete deterministic checksum inventory for one release root."""

    root = release_root.expanduser().resolve()
    target = _relative_path(root, relative_path, label="checksum inventory")
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"{sha256_file(path)}  {path.relative_to(root).as_posix()}"
        for path in iter_release_files(root)
        if path.resolve() != target
    ]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def verify_checksums(
    release_root: Path,
    *,
    relative_path: str = "metadata/checksums.sha256",
) -> None:
    """Verify the checksum inventory exactly, including missing/extra files."""

    root = release_root.expanduser().resolve()
    target = _relative_file(root, relative_path, label="checksum inventory")
    expected: dict[str, str] = {}
    for line in target.read_text(encoding="utf-8").splitlines():
        pieces = line.split("  ", 1)
        if len(pieces) != 2 or SHA256.fullmatch(pieces[0]) is None:
            raise DepthSchemaError("checksum inventory contains a malformed line")
        digest, relative = pieces
        if relative in expected:
            raise DepthSchemaError(f"checksum path is repeated: {relative}")
        expected[relative] = digest
    actual = {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in iter_release_files(root)
        if path.resolve() != target
    }
    if expected != actual:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        changed = sorted(
            path
            for path in set(expected) & set(actual)
            if expected[path] != actual[path]
        )
        raise DepthSchemaError(
            "checksum inventory drifted: "
            f"missing={missing}, extra={extra}, changed={changed}"
        )


__all__ = [
    "ANCHOR_ONLY_PARENT_IDS",
    "APPROVED_REPRESENTATION_COUNT",
    "CORE_EXTRA_ROW_COUNT",
    "CORE_ROW_COLUMNS",
    "CORE_ROW_COUNT",
    "CORE_SCHEMA_VERSION",
    "DEPTH_CONTROL_COLUMNS",
    "DEPTH_DESCENDANT_COUNT",
    "DEPTH_ELIGIBLE_COUNT",
    "DEPTH_ROW_COLUMNS",
    "DEPTH_ROW_COUNT",
    "DEPTH_SCHEMA_VERSION",
    "DepthSchemaError",
    "EXPECTED_SPLIT_COUNTS",
    "EXPECTED_STATE_IDS",
    "FREEZE_SCHEMA_VERSION",
    "FROZEN_LOGICAL_RELEASE_SHA256",
    "GEOMETRY_STATE_COUNT",
    "MANIFEST_SCHEMA_VERSION",
    "RELEASE_NAME",
    "ShardPlan",
    "TRAIN_ROW_COUNT",
    "VALIDATION_ROW_COUNT",
    "bind_logical_row_sha256",
    "build_freeze",
    "build_manifest",
    "canonical_json",
    "canonical_sha256",
    "depth_features",
    "iter_release_files",
    "logical_release_sha256",
    "logical_row_record",
    "logical_row_sha256",
    "plan_shards",
    "sha256_file",
    "shard_filename",
    "validate_depth_population",
    "verify_checksums",
    "verify_logical_row_sha256",
    "write_checksums",
    "write_json",
]
