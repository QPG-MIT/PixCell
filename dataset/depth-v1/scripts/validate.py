#!/usr/bin/env python3
"""Validate a built PixCell depth-v1 release against frozen core-v1.

The default pass is entirely local and static.  It verifies the depth-v1
checksum inventory, freeze, manifests, Parquet shards, complete population,
embedded core payloads, controlled literal deltas, normalized source grammar,
and every code/image digest.  ``--execute-programs`` additionally executes the
published programs and rechecks geometry, ports, raster evidence, and rendered
descendant images.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from PIL import Image


SCRIPT_ROOT = Path(__file__).resolve().parent
DEPTH_ROOT = SCRIPT_ROOT.parent
DATASET_ROOT = DEPTH_ROOT.parent
CORE_SCRIPTS = DATASET_ROOT / "scripts"
sys.path.insert(0, str(CORE_SCRIPTS))
sys.path.insert(0, str(SCRIPT_ROOT))

from _shared import (  # noqa: E402
    LEVELS,
    SAFE_PUBLIC_ID,
    forbidden_release_imports,
    normalized_d4_sha256,
    primitive_calls,
    purity_violations,
    scan_value_strings,
    sha256_bytes,
    sha256_file,
    top_level_parameters,
)
from contracts import normalized_grammar_hash, top_level_literals  # noqa: E402
from runtime import (  # noqa: E402
    execute_program,
    mask_delta,
    render_geometry,
    render_views,
    validate_candidate,
)
from schema import (  # noqa: E402
    ANCHOR_ONLY_PARENT_IDS,
    APPROVED_REPRESENTATION_COUNT,
    CORE_ROW_COLUMNS,
    CORE_ROW_COUNT,
    DEPTH_ELIGIBLE_COUNT,
    DEPTH_ROW_COLUMNS,
    DEPTH_SCHEMA_VERSION,
    EXPECTED_SPLIT_COUNTS,
    FREEZE_SCHEMA_VERSION,
    FROZEN_LOGICAL_RELEASE_SHA256,
    GEOMETRY_STATE_COUNT,
    MANIFEST_SCHEMA_VERSION,
    PROHIBITED_EVIDENCE_KEY_PARTS,
    DepthSchemaError,
    build_freeze,
    build_manifest,
    canonical_sha256,
    depth_features,
    logical_release_sha256,
    validate_depth_population,
    verify_checksums,
)


class DepthValidationError(RuntimeError):
    """Raised when a published depth-v1 invariant does not hold."""


def _validate_frozen_logical_release(
    manifest: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
) -> None:
    stored_digest = manifest.get("logical_release_sha256")
    if stored_digest != FROZEN_LOGICAL_RELEASE_SHA256:
        raise DepthValidationError(
            "manifest logical release digest differs from frozen depth-v1"
        )
    try:
        observed_digest = logical_release_sha256(rows)
    except DepthSchemaError as exc:
        raise DepthValidationError(str(exc)) from exc
    if observed_digest != FROZEN_LOGICAL_RELEASE_SHA256:
        raise DepthValidationError(
            "recomputed logical release digest differs from frozen depth-v1"
        )


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise DepthValidationError(f"required JSON file is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DepthValidationError(f"invalid JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise DepthValidationError(f"JSON root must be an object: {path}")
    return value


def _json_value(row_id: str, field: str, value: Any) -> Any:
    if not isinstance(value, str):
        raise DepthValidationError(f"{row_id}: {field} is not JSON text")
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise DepthValidationError(f"{row_id}: malformed {field}") from exc


def _json_object(row_id: str, field: str, value: Any) -> dict[str, Any]:
    parsed = _json_value(row_id, field, value)
    if not isinstance(parsed, dict):
        raise DepthValidationError(f"{row_id}: {field} must encode an object")
    return parsed


def _reject_control_keys(value: Any, *, label: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(part in lowered for part in PROHIBITED_EVIDENCE_KEY_PARTS):
                raise DepthValidationError(
                    f"{label}: forbidden public control key {key!r}"
                )
            _reject_control_keys(child, label=label)
    elif isinstance(value, list):
        for child in value:
            _reject_control_keys(child, label=label)


def _embedded_png(
    row_id: str,
    field: str,
    value: Any,
    expected_sha256: Any,
) -> tuple[bytes, Image.Image]:
    if not isinstance(value, dict) or not value.get("bytes"):
        raise DepthValidationError(f"{row_id}: {field} is not embedded")
    payload = bytes(value["bytes"])
    if sha256_bytes(payload) != expected_sha256:
        raise DepthValidationError(f"{row_id}: {field} hash mismatch")
    try:
        with Image.open(io.BytesIO(payload)) as opened:
            opened.verify()
        image = Image.open(io.BytesIO(payload)).convert("L")
    except OSError as exc:
        raise DepthValidationError(f"{row_id}: invalid {field} PNG") from exc
    extrema = image.getextrema()
    if extrema[0] == extrema[1]:
        raise DepthValidationError(f"{row_id}: blank {field}")
    return payload, image


def _literal_map(code: str) -> dict[str, Any]:
    return {
        assignment.name: assignment.value for assignment in top_level_literals(code)
    }


def _json_normalize(value: Any) -> Any:
    return json.loads(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    )


def _validate_parameter_payload(
    row_id: str,
    code: str,
    payload: Mapping[str, Any],
    *,
    anchor_payload: Mapping[str, Any] | None = None,
) -> None:
    if set(payload) != {"fixed_context", "parameters"}:
        raise DepthValidationError(
            f"{row_id}: parameters_json must contain exactly "
            "fixed_context and parameters"
        )
    fixed_context = payload.get("fixed_context")
    parameters = payload.get("parameters")
    if not isinstance(fixed_context, dict) or not isinstance(parameters, dict):
        raise DepthValidationError(f"{row_id}: malformed parameters_json sections")
    live_values = _json_normalize(top_level_parameters(code))
    missing = sorted(set(parameters) - set(live_values))
    if missing:
        raise DepthValidationError(
            f"{row_id}: declared parameters absent from code: {missing}"
        )
    observed = {name: live_values[name] for name in parameters}
    if parameters != observed:
        raise DepthValidationError(
            f"{row_id}: declared parameter values differ from code"
        )
    if anchor_payload is None:
        return
    if set(anchor_payload) != {"fixed_context", "parameters"}:
        raise DepthValidationError(f"{row_id}: parent parameter contract is malformed")
    anchor_fixed = anchor_payload.get("fixed_context")
    anchor_parameters = anchor_payload.get("parameters")
    if not isinstance(anchor_fixed, dict) or not isinstance(anchor_parameters, dict):
        raise DepthValidationError(
            f"{row_id}: parent parameter contract sections are malformed"
        )
    if fixed_context != anchor_fixed:
        raise DepthValidationError(f"{row_id}: fixed_context differs from parent")
    if set(parameters) != set(anchor_parameters):
        raise DepthValidationError(
            f"{row_id}: declared parameter keys differ from parent"
        )


def _validate_row_static(row: Mapping[str, Any]) -> dict[str, Any]:
    row_id = str(row.get("id", ""))
    if not row_id or SAFE_PUBLIC_ID.fullmatch(row_id) is None:
        raise DepthValidationError(f"unsafe or empty row ID: {row_id!r}")
    hits = scan_value_strings(row_id, row)
    if hits:
        raise DepthValidationError("; ".join(hits))
    if tuple(row) != DEPTH_ROW_COLUMNS:
        raise DepthValidationError(f"{row_id}: depth column order drift")
    if row["depth_schema_version"] != DEPTH_SCHEMA_VERSION:
        raise DepthValidationError(f"{row_id}: depth schema version drift")
    if row["code_language"] != "python":
        raise DepthValidationError(f"{row_id}: code_language must be python")

    code = row["code"]
    if not isinstance(code, str):
        raise DepthValidationError(f"{row_id}: code is not text")
    try:
        compile(code, f"{row_id}/ground_truth.py", "exec")
    except SyntaxError as exc:
        raise DepthValidationError(f"{row_id}: code does not compile: {exc}") from exc
    violations = purity_violations(code)
    if violations:
        raise DepthValidationError(f"{row_id}: purity violations: {violations}")
    forbidden = forbidden_release_imports(code)
    if forbidden:
        raise DepthValidationError(f"{row_id}: forbidden imports: {forbidden}")
    if sha256_bytes(code.encode("utf-8")) != row["code_sha256"]:
        raise DepthValidationError(f"{row_id}: code hash mismatch")
    observed_calls = primitive_calls(code)
    if observed_calls != row["primitive_calls"]:
        raise DepthValidationError(f"{row_id}: primitive call inventory drift")

    parsed = {
        "port_signature_json": _json_value(
            row_id,
            "port_signature_json",
            row["port_signature_json"],
        ),
        "parameters_json": _json_object(
            row_id,
            "parameters_json",
            row["parameters_json"],
        ),
        "topology_json": _json_value(
            row_id,
            "topology_json",
            row["topology_json"],
        ),
        "metadata_json": _json_value(
            row_id,
            "metadata_json",
            row["metadata_json"],
        ),
        "parameter_delta_json": _json_object(
            row_id,
            "parameter_delta_json",
            row["parameter_delta_json"],
        ),
        "verification_evidence_json": _json_object(
            row_id,
            "verification_evidence_json",
            row["verification_evidence_json"],
        ),
    }
    _reject_control_keys(
        parsed["verification_evidence_json"],
        label=f"{row_id}/verification_evidence_json",
    )
    _validate_parameter_payload(row_id, code, parsed["parameters_json"])

    footprint = row["footprint_um"]
    if (
        not isinstance(footprint, list)
        or len(footprint) != 2
        or any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or float(value) <= 0
            for value in footprint
        )
    ):
        raise DepthValidationError(f"{row_id}: invalid footprint")

    _image_bytes, image = _embedded_png(
        row_id,
        "image",
        row["image"],
        row["image_sha256"],
    )
    _embedded_png(
        row_id,
        "target_image",
        row["target_image"],
        row["target_image_sha256"],
    )
    if normalized_d4_sha256(image) != row["normalized_d4_sha256"]:
        raise DepthValidationError(f"{row_id}: normalized D4 witness mismatch")
    return parsed


def _core_parquet_paths(dataset_root: Path) -> list[Path]:
    paths: list[Path] = []
    for level in LEVELS:
        matches = sorted((dataset_root / "data" / level).glob("train-*.parquet"))
        if len(matches) != 1:
            raise DepthValidationError(
                f"{level}: expected one core-v1 shard, found {len(matches)}"
            )
        paths.append(matches[0])
    return paths


def _load_frozen_core(
    dataset_root: Path,
    *,
    expected_digest: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    freeze = _read_json_object(dataset_root / "factory" / "core-v1" / "freeze.json")
    if freeze.get("release_digest_sha256") != expected_digest:
        raise DepthValidationError("depth parent digest differs from frozen core-v1")
    references = freeze.get("reference_artifacts")
    if not isinstance(references, dict) or not references:
        raise DepthValidationError("core-v1 freeze has no reference artifact map")
    for relative, digest in sorted(references.items()):
        path = dataset_root / relative
        if not path.is_file() or sha256_file(path) != digest:
            raise DepthValidationError(f"frozen core-v1 artifact drift: {relative}")

    rows: list[dict[str, Any]] = []
    for path in _core_parquet_paths(dataset_root):
        table = pq.read_table(path)
        if tuple(table.schema.names) != CORE_ROW_COLUMNS:
            raise DepthValidationError(f"core schema drift: {path}")
        rows.extend(table.to_pylist())
    if len(rows) != CORE_ROW_COUNT:
        raise DepthValidationError(f"core-v1 row count {len(rows)} != {CORE_ROW_COUNT}")
    if len({str(row["id"]) for row in rows}) != len(rows):
        raise DepthValidationError("core-v1 row IDs are not unique")
    return rows, freeze


def _load_depth_shards(
    release_root: Path,
    manifest: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    raw_shards = manifest.get("shards")
    if not isinstance(raw_shards, list) or not raw_shards:
        raise DepthValidationError("manifest has no shard records")
    expected_paths: set[str] = set()
    rows_by_split: dict[str, list[dict[str, Any]]] = {
        "train": [],
        "validation": [],
    }
    expected_schema = depth_features().arrow_schema
    for record in raw_shards:
        if not isinstance(record, dict):
            raise DepthValidationError("manifest shard record is malformed")
        split = str(record.get("split", ""))
        relative = str(record.get("path", ""))
        if split not in rows_by_split:
            raise DepthValidationError(f"unknown shard split: {split!r}")
        raw_path = Path(relative)
        if (
            not relative
            or raw_path.is_absolute()
            or ".." in raw_path.parts
            or raw_path.parent != Path("data")
            or raw_path.suffix != ".parquet"
            or relative in expected_paths
        ):
            raise DepthValidationError(f"unsafe or repeated shard path: {relative!r}")
        expected_paths.add(relative)
        path = release_root / raw_path
        if not path.is_file():
            raise DepthValidationError(f"manifest shard is missing: {relative}")
        if path.stat().st_size != record.get("bytes"):
            raise DepthValidationError(f"{relative}: byte size differs from manifest")
        if sha256_file(path) != record.get("sha256"):
            raise DepthValidationError(f"{relative}: hash differs from manifest")
        table = pq.read_table(path)
        _validate_arrow_schema(relative, table.schema, expected_schema)
        shard_rows = table.to_pylist()
        if len(shard_rows) != record.get("rows"):
            raise DepthValidationError(f"{relative}: row count differs from manifest")
        rows_by_split[split].extend(shard_rows)

    actual_paths = {
        path.relative_to(release_root).as_posix()
        for path in (release_root / "data").glob("*.parquet")
    }
    if actual_paths != expected_paths:
        raise DepthValidationError(
            "Parquet inventory differs from manifest: "
            f"missing={sorted(expected_paths - actual_paths)}, "
            f"extra={sorted(actual_paths - expected_paths)}"
        )
    for split, expected in EXPECTED_SPLIT_COUNTS.items():
        if len(rows_by_split[split]) != expected:
            raise DepthValidationError(
                f"{split}: {len(rows_by_split[split])} rows != {expected}"
            )
    return [
        *rows_by_split["train"],
        *rows_by_split["validation"],
    ], rows_by_split


def _validate_arrow_schema(
    relative: str,
    actual_schema: Any,
    expected_schema: Any,
) -> None:
    if not actual_schema.equals(expected_schema, check_metadata=False):
        raise DepthValidationError(f"{relative}: Arrow schema differs")
    expected_huggingface = (expected_schema.metadata or {}).get(b"huggingface")
    actual_huggingface = (actual_schema.metadata or {}).get(b"huggingface")
    if (
        expected_huggingface is None
        or actual_huggingface != expected_huggingface
    ):
        raise DepthValidationError(
            f"{relative}: Hugging Face feature metadata differs"
        )


def _validate_controlled_relationship(
    row: Mapping[str, Any],
    anchor: Mapping[str, Any],
    *,
    parsed_delta: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> None:
    row_id = str(row["id"])
    if row["leakage_group_id"] != anchor["leakage_group_id"]:
        raise DepthValidationError(f"{row_id}: leakage_group_id differs from parent")
    _validate_parameter_payload(
        row_id,
        str(row["code"]),
        _json_object(row_id, "parameters_json", row["parameters_json"]),
        anchor_payload=_json_object(
            str(anchor["id"]),
            "parameters_json",
            anchor["parameters_json"],
        ),
    )
    controlled = list(row["controlled_axes"])
    if not controlled:
        raise DepthValidationError(f"{row_id}: controlled row has no axes")
    changes = parsed_delta.get("changes")
    if not isinstance(changes, dict) or set(changes) != set(controlled):
        raise DepthValidationError(
            f"{row_id}: delta changes differ from controlled_axes"
        )

    before = _literal_map(str(anchor["code"]))
    after = _literal_map(str(row["code"]))
    if before.keys() != after.keys():
        raise DepthValidationError(f"{row_id}: top-level literal set changed")
    for name, record in changes.items():
        if name not in before or not isinstance(record, dict):
            raise DepthValidationError(f"{row_id}: malformed delta for {name}")
        if record.get("before") != before[name] or record.get("after") != after[name]:
            raise DepthValidationError(f"{row_id}: delta witness differs for {name}")
        if before[name] == after[name]:
            raise DepthValidationError(f"{row_id}: controlled axis {name} is a no-op")

    derived = parsed_delta.get("derived_updates", [])
    if not isinstance(derived, list) or any(
        not isinstance(name, str) or name not in before for name in derived
    ):
        raise DepthValidationError(f"{row_id}: malformed derived update list")
    expected_changed = set(controlled)
    expected_changed.update(
        name for name in derived if before.get(name) != after.get(name)
    )
    observed_changed = {name for name in before if before[name] != after[name]}
    if observed_changed != expected_changed:
        raise DepthValidationError(
            f"{row_id}: literal delta changed unapproved fields "
            f"{sorted(observed_changed ^ expected_changed)}"
        )

    anchor_hash = normalized_grammar_hash(str(anchor["code"]))
    candidate_hash = normalized_grammar_hash(str(row["code"]))
    if anchor_hash != candidate_hash:
        raise DepthValidationError(f"{row_id}: normalized source grammar changed")
    if evidence.get("normalized_grammar_hash") != anchor_hash:
        raise DepthValidationError(f"{row_id}: recorded grammar hash differs")
    model_signal = evidence.get("model_input_signal")
    if (
        not isinstance(model_signal, dict)
        or not isinstance(model_signal.get("footprint_changed"), bool)
        or (
            model_signal.get("normalized_changed_fraction") is not None
            and not isinstance(
                model_signal.get("normalized_changed_fraction"),
                (int, float),
            )
        )
    ):
        raise DepthValidationError(f"{row_id}: malformed model-input evidence")
    if primitive_calls(str(row["code"])) != primitive_calls(str(anchor["code"])):
        raise DepthValidationError(f"{row_id}: primitive API set differs from parent")


def _validate_core_relationships(
    rows: Sequence[Mapping[str, Any]],
    core_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    core_by_id = {str(row["id"]): row for row in core_rows}
    semantic_by_grammar: dict[str, Mapping[str, Any]] = {}
    for core in core_rows:
        if core["variation_role"] != "semantic":
            continue
        grammar_id = str(core["grammar_id"])
        if grammar_id in semantic_by_grammar:
            raise DepthValidationError(
                f"{grammar_id}: more than one semantic core anchor"
            )
        semantic_by_grammar[grammar_id] = core
    if len(semantic_by_grammar) != APPROVED_REPRESENTATION_COUNT:
        raise DepthValidationError(
            "frozen core does not contain 547 semantic representations"
        )
    anchor_by_id = {
        str(anchor["id"]): anchor for anchor in semantic_by_grammar.values()
    }

    wrapped = [row for row in rows if int(row["realization_slot"]) in {-1, 0}]
    if len(wrapped) != CORE_ROW_COUNT:
        raise DepthValidationError("depth release does not embed all 738 core rows")
    if {str(row["id"]) for row in wrapped} != set(core_by_id):
        raise DepthValidationError("embedded core ID inventory differs from core-v1")
    for row in wrapped:
        core = core_by_id[str(row["id"])]
        differences = [
            column for column in CORE_ROW_COLUMNS if row[column] != core[column]
        ]
        if differences:
            raise DepthValidationError(
                f"{row['id']}: embedded core payload drift: {differences}"
            )

    for row in rows:
        row_id = str(row["id"])
        parent_id = str(row["parent_core_id"])
        anchor = anchor_by_id.get(parent_id)
        if anchor is None:
            raise DepthValidationError(f"{row_id}: unknown semantic parent {parent_id}")
        if row["parent_code_sha256"] != anchor["code_sha256"]:
            raise DepthValidationError(f"{row_id}: parent code hash differs")
        if row["grammar_id"] != anchor["grammar_id"]:
            raise DepthValidationError(f"{row_id}: grammar differs from parent")
        if row["representation_id"] != anchor["representation_id"]:
            raise DepthValidationError(f"{row_id}: representation differs from parent")
        if row["leakage_group_id"] != anchor["leakage_group_id"]:
            raise DepthValidationError(
                f"{row_id}: leakage_group_id differs from parent"
            )
        slot = int(row["realization_slot"])
        if slot <= 0:
            if row["controlled_axes"]:
                raise DepthValidationError(f"{row_id}: core row has controlled axes")
            continue
        expected_id = f"{parent_id}__depth_r{slot:02d}"
        if row_id != expected_id:
            raise DepthValidationError(
                f"{row_id}: controlled row ID should be {expected_id}"
            )
        if row["variation_role"] != "controlled_realization":
            raise DepthValidationError(f"{row_id}: controlled row variation_role drift")
        parsed_delta = _json_object(
            row_id,
            "parameter_delta_json",
            row["parameter_delta_json"],
        )
        evidence = _json_object(
            row_id,
            "verification_evidence_json",
            row["verification_evidence_json"],
        )
        _validate_controlled_relationship(
            row,
            anchor,
            parsed_delta=parsed_delta,
            evidence=evidence,
        )
    return anchor_by_id


def _verify_freeze_and_manifests(
    release_root: Path,
    dataset_root: Path,
    manifest: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    anchors: Mapping[str, Mapping[str, Any]],
) -> dict[str, set[str]]:
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise DepthValidationError("manifest schema version drift")
    expected_manifest = build_manifest(
        rows,
        shards=manifest.get("shards", []),
        depth_generator_version=str(manifest.get("depth_generator_version", "")),
        expected_parent_core_digest_sha256=str(
            manifest.get("parent_core_digest_sha256", "")
        ),
    )
    if dict(manifest) != expected_manifest:
        raise DepthValidationError("manifest differs from recomputed population")

    freeze = _read_json_object(release_root / "factory" / "freeze.json")
    if freeze.get("schema_version") != FREEZE_SCHEMA_VERSION:
        raise DepthValidationError("freeze schema version drift")
    references = freeze.get("reference_artifacts")
    if not isinstance(references, dict) or not references:
        raise DepthValidationError("depth freeze has no reference artifact map")
    rebuilt_freeze = build_freeze(
        release_root,
        manifest,
        manifest_path="metadata/manifest.json",
        reference_paths=sorted(references),
    )
    if freeze != rebuilt_freeze:
        raise DepthValidationError("depth freeze differs from referenced artifacts")

    core_snapshot = _read_json_object(
        release_root / "factory" / "core_reference_snapshot.json"
    )
    if core_snapshot.get("core_digest_sha256") != manifest.get(
        "parent_core_digest_sha256"
    ):
        raise DepthValidationError("core reference snapshot digest differs")
    core_freeze = _read_json_object(
        dataset_root / "factory" / "core-v1" / "freeze.json"
    )
    if core_snapshot.get("reference_artifacts") != core_freeze.get(
        "reference_artifacts"
    ):
        raise DepthValidationError("core reference snapshot is incomplete or changed")

    anchor_manifest = _read_json_object(
        release_root / "factory" / "anchor_manifest.json"
    )
    if anchor_manifest.get("core_digest_sha256") != manifest.get(
        "parent_core_digest_sha256"
    ):
        raise DepthValidationError("anchor manifest core digest differs")
    grammar_catalog = dataset_root / "factory" / "core-v1" / "grammar_catalog.json"
    if anchor_manifest.get("core_grammar_catalog_sha256") != sha256_file(
        grammar_catalog
    ):
        raise DepthValidationError("anchor manifest grammar catalog hash differs")
    expected_anchors = [
        {
            "code_sha256": anchor["code_sha256"],
            "grammar_id": anchor["grammar_id"],
            "id": anchor["id"],
            "image_sha256": anchor["image_sha256"],
            "level": anchor["level"],
        }
        for anchor in sorted(
            anchors.values(),
            key=lambda item: (str(item["level"]), str(item["id"])),
        )
    ]
    if (
        anchor_manifest.get("representation_count") != APPROVED_REPRESENTATION_COUNT
        or anchor_manifest.get("anchors") != expected_anchors
    ):
        raise DepthValidationError("anchor manifest differs from frozen core anchors")

    accepted = _read_json_object(release_root / "factory" / "accepted_manifest.json")
    expected_accepted_rows = [
        {
            "code_sha256": row["code_sha256"],
            "geometry_id": row["geometry_id"],
            "grammar_id": row["grammar_id"],
            "id": row["id"],
            "image_sha256": row["image_sha256"],
            "logical_row_sha256": row["logical_row_sha256"],
            "realization_id": row["realization_id"],
            "split_role": row["split_role"],
            "target_image_sha256": row["target_image_sha256"],
        }
        for row in sorted(rows, key=lambda item: str(item["id"]))
    ]
    if (
        accepted.get("accepted_only") is not True
        or accepted.get("generator_version") != manifest.get("depth_generator_version")
        or accepted.get("row_count") != len(rows)
        or accepted.get("rows") != expected_accepted_rows
    ):
        raise DepthValidationError("accepted manifest differs from Parquet rows")

    plans = _read_json_object(release_root / "factory" / "generation_plan.json")
    plan_records = plans.get("plans")
    if (
        plans.get("generator_version") != manifest.get("depth_generator_version")
        or plans.get("geometry_states_per_complete_representation")
        != GEOMETRY_STATE_COUNT
        or plans.get("representation_count") != APPROVED_REPRESENTATION_COUNT
        or plans.get("anchor_representation_count")
        != APPROVED_REPRESENTATION_COUNT
        or plans.get("complete_depth_representation_count")
        != DEPTH_ELIGIBLE_COUNT
        or plans.get("anchor_only_representation_count")
        != len(ANCHOR_ONLY_PARENT_IDS)
        or plans.get("anchor_only_parent_ids")
        != sorted(ANCHOR_ONLY_PARENT_IDS)
        or not isinstance(plan_records, list)
        or len(plan_records) != APPROVED_REPRESENTATION_COUNT
    ):
        raise DepthValidationError("generation plan population differs")
    plans_by_parent: dict[str, list[dict[str, Any]]] = {}
    controlled_by_parent = {
        (str(row["parent_core_id"]), str(row["realization_id"])): row
        for row in rows
        if int(row["realization_slot"]) > 0
    }
    for plan in plan_records:
        if not isinstance(plan, dict):
            raise DepthValidationError("malformed generation plan")
        parent_id = str(plan.get("anchor_id", ""))
        anchor = anchors.get(parent_id)
        states = plan.get("states")
        expected_state_count = (
            0
            if parent_id in ANCHOR_ONLY_PARENT_IDS
            else GEOMETRY_STATE_COUNT - 1
        )
        if (
            anchor is None
            or parent_id in plans_by_parent
            or plan.get("grammar_id") != anchor["grammar_id"]
            or plan.get("level") != anchor["level"]
            or not isinstance(states, list)
            or len(states) != expected_state_count
        ):
            raise DepthValidationError(f"{parent_id}: generation plan differs")
        plans_by_parent[parent_id] = states
        for state in states:
            if not isinstance(state, dict):
                raise DepthValidationError(f"{parent_id}: malformed plan state")
            axis_ids = state.get("axis_ids")
            if (
                not isinstance(axis_ids, list)
                or not axis_ids
                or any(
                    not isinstance(axis_id, str) or not axis_id for axis_id in axis_ids
                )
            ):
                raise DepthValidationError(f"{parent_id}: malformed plan axis IDs")
            row = controlled_by_parent.get(
                (parent_id, str(state.get("realization_id", "")))
            )
            if row is None:
                raise DepthValidationError(f"{parent_id}: plan state has no row")
            expected_state = {
                "axis_ids": state.get("axis_ids"),
                "code_sha256": row["code_sha256"],
                "controlled_axes": row["controlled_axes"],
                "geometry_id": row["geometry_id"],
                "image_sha256": row["image_sha256"],
                "parameter_delta": json.loads(row["parameter_delta_json"]),
                "realization_id": row["realization_id"],
                "target_image_sha256": row["target_image_sha256"],
                "verification_evidence_sha256": canonical_sha256(
                    json.loads(row["verification_evidence_json"])
                ),
            }
            if state != expected_state:
                raise DepthValidationError(
                    f"{row['id']}: generation plan state differs"
                )
    if set(plans_by_parent) != set(anchors):
        raise DepthValidationError("generation plan parent inventory differs")

    contracts = _read_json_object(release_root / "factory" / "variation_contracts.json")
    contract_records = contracts.get("contracts")
    if (
        contracts.get("generator_version") != manifest.get("depth_generator_version")
        or contracts.get("representation_count") != APPROVED_REPRESENTATION_COUNT
        or contracts.get("anchor_representation_count")
        != APPROVED_REPRESENTATION_COUNT
        or contracts.get("complete_depth_representation_count")
        != DEPTH_ELIGIBLE_COUNT
        or contracts.get("anchor_only_representation_count")
        != len(ANCHOR_ONLY_PARENT_IDS)
        or contracts.get("anchor_only_parent_ids")
        != sorted(ANCHOR_ONLY_PARENT_IDS)
        or not isinstance(contract_records, list)
        or len(contract_records) != APPROVED_REPRESENTATION_COUNT
    ):
        raise DepthValidationError("variation contract population differs")
    seen_contracts: set[str] = set()
    qualified_by_anchor: dict[str, set[str]] = {}
    repeat_names_by_anchor: dict[str, set[str]] = {}
    for contract in contract_records:
        if not isinstance(contract, dict):
            raise DepthValidationError("malformed variation contract")
        anchor_id = str(contract.get("anchor_id", ""))
        anchor = anchors.get(anchor_id)
        if anchor is None or anchor_id in seen_contracts:
            raise DepthValidationError(f"unknown/repeated contract: {anchor_id}")
        seen_contracts.add(anchor_id)
        if contract.get("grammar_id") != anchor["grammar_id"] or contract.get(
            "source_grammar_hash"
        ) != normalized_grammar_hash(str(anchor["code"])):
            raise DepthValidationError(f"{anchor_id}: contract grammar hash differs")
        axes = contract.get("axes")
        qualified = contract.get("qualified_axis_ids")
        assignments = contract.get("assignments")
        expected_qualified_empty = anchor_id in ANCHOR_ONLY_PARENT_IDS
        if (
            not isinstance(axes, list)
            or not isinstance(qualified, list)
            or (not qualified) != expected_qualified_empty
            or not isinstance(assignments, list)
            or not set(qualified).issubset(
                {
                    str(axis.get("axis_id", ""))
                    for axis in axes
                    if isinstance(axis, dict)
                }
            )
        ):
            raise DepthValidationError(f"{anchor_id}: qualified axes are malformed")
        qualified_by_anchor[anchor_id] = set(map(str, qualified))
        repeat_names_by_anchor[anchor_id] = {
            str(assignment.get("name", ""))
            for assignment in assignments
            if isinstance(assignment, dict)
            and assignment.get("parameter_class") == "realization_repeat_count"
        }
    if seen_contracts != set(anchors):
        raise DepthValidationError("variation contract parent inventory differs")
    for anchor_id, states in plans_by_parent.items():
        qualified = qualified_by_anchor[anchor_id]
        for state in states:
            if not set(map(str, state["axis_ids"])).issubset(qualified):
                raise DepthValidationError(
                    f"{anchor_id}: plan uses an unqualified parameter axis"
                )

    catalog = _read_json_object(release_root / "metadata" / "catalog.json")
    level_counts = dict(sorted(Counter(str(row["level"]) for row in rows).items()))
    if (
        catalog.get("accepted_only") is not True
        or catalog.get("columns") != list(DEPTH_ROW_COLUMNS)
        or catalog.get("generator_version") != manifest.get("depth_generator_version")
        or catalog.get("level_counts") != level_counts
        or catalog.get("row_count") != len(rows)
        or catalog.get("representation_count") != len(anchors)
        or catalog.get("anchor_representation_count") != len(anchors)
        or catalog.get("complete_depth_representation_count")
        != DEPTH_ELIGIBLE_COUNT
        or catalog.get("anchor_only_representation_count")
        != len(ANCHOR_ONLY_PARENT_IDS)
        or catalog.get("anchor_only_parent_ids")
        != sorted(ANCHOR_ONLY_PARENT_IDS)
        or catalog.get("logical_release_sha256") != logical_release_sha256(rows)
        or catalog.get("split_counts") != manifest.get("split_counts")
    ):
        raise DepthValidationError("metadata catalog differs from release")
    audit = _read_json_object(release_root / "metadata" / "audit_report.json")
    controlled_counts = Counter(axis for row in rows for axis in row["controlled_axes"])
    transform_counts = Counter(str(row["transform_kind"]) for row in rows)
    expected_verification_keys = {
        "all_controlled_programs_compiled_and_pure",
        "all_controlled_programs_executed",
        "all_controlled_source_grammars_preserved",
        "all_geometry_changes_have_input_signal",
        "all_ports_attached_and_signature_preserved",
        "all_representation_ids_come_from_core_v1",
    }
    audit_verification = audit.get("verification")
    if (
        audit.get("accepted_only") is not True
        or audit.get("controlled_axis_counts")
        != dict(sorted(controlled_counts.items()))
        or audit.get("geometry_states_per_complete_representation")
        != GEOMETRY_STATE_COUNT
        or audit.get("row_count") != len(rows)
        or audit.get("representation_count") != len(anchors)
        or audit.get("anchor_representation_count") != len(anchors)
        or audit.get("complete_depth_representation_count")
        != DEPTH_ELIGIBLE_COUNT
        or audit.get("anchor_only_representation_count")
        != len(ANCHOR_ONLY_PARENT_IDS)
        or audit.get("anchor_only_parent_ids")
        != sorted(ANCHOR_ONLY_PARENT_IDS)
        or audit.get("transform_counts") != dict(sorted(transform_counts.items()))
        or audit.get("logical_release_sha256") != manifest.get("logical_release_sha256")
        or audit.get("core_reference_match") is not True
        or not isinstance(audit_verification, dict)
        or set(audit_verification) != expected_verification_keys
        or any(value is not True for value in audit_verification.values())
    ):
        raise DepthValidationError("audit report differs from release")

    gallery = _read_json_object(release_root / "metadata" / "gallery_manifest.json")
    gallery_pages = gallery.get("pages")
    if (
        gallery.get("anchor_representation_count")
        != APPROVED_REPRESENTATION_COUNT
        or gallery.get("progression_representation_count")
        != DEPTH_ELIGIBLE_COUNT
        or gallery.get("anchor_only_parent_ids")
        != sorted(ANCHOR_ONLY_PARENT_IDS)
        or gallery.get("state_slots")
        != [f"r{slot:02d}" for slot in range(GEOMETRY_STATE_COUNT)]
        or not isinstance(gallery_pages, list)
        or gallery.get("progression_page_count") != len(gallery_pages)
    ):
        raise DepthValidationError("gallery manifest population differs")
    if gallery.get("overview") != "galleries/overview.png":
        raise DepthValidationError("gallery overview path differs")
    gallery_paths = [str(gallery["overview"])]
    seen_gallery_grammars: set[str] = set()
    for page in gallery_pages:
        if not isinstance(page, dict):
            raise DepthValidationError("malformed gallery page record")
        gallery_paths.append(str(page.get("path", "")))
        grammar_ids = page.get("representation_ids")
        level = page.get("level")
        if (
            not isinstance(grammar_ids, list)
            or any(not isinstance(grammar_id, str) for grammar_id in grammar_ids)
            or len(grammar_ids) != len(set(grammar_ids))
            or bool(set(grammar_ids) & seen_gallery_grammars)
            or not isinstance(level, str)
            or level.lower() not in LEVELS
        ):
            raise DepthValidationError("gallery grammar inventory is malformed")
        expected_level_ids = {
            str(anchor["grammar_id"])
            for parent_id, anchor in anchors.items()
            if parent_id not in ANCHOR_ONLY_PARENT_IDS
            and anchor["level"] == level
        }
        if not set(grammar_ids).issubset(expected_level_ids):
            raise DepthValidationError("gallery page mixes representation levels")
        seen_gallery_grammars.update(grammar_ids)
    expected_gallery_grammars = {
        str(anchor["grammar_id"])
        for parent_id, anchor in anchors.items()
        if parent_id not in ANCHOR_ONLY_PARENT_IDS
    }
    if seen_gallery_grammars != expected_gallery_grammars:
        raise DepthValidationError(
            "progression gallery does not cover every complete-depth representation"
        )
    for relative in gallery_paths:
        raw = Path(relative)
        if (
            not relative
            or raw.is_absolute()
            or ".." in raw.parts
            or not (release_root / raw).is_file()
        ):
            raise DepthValidationError(f"missing or unsafe gallery path: {relative}")
    actual_progression_paths = {
        path.relative_to(release_root).as_posix()
        for path in (release_root / "galleries" / "progressions").glob("*.png")
    }
    expected_progression_paths = set(gallery_paths[1:])
    if actual_progression_paths != expected_progression_paths:
        raise DepthValidationError(
            "progression gallery file inventory differs: "
            f"missing={sorted(expected_progression_paths - actual_progression_paths)}, "
            f"extra={sorted(actual_progression_paths - expected_progression_paths)}"
        )

    for path in sorted(
        [
            *(release_root / "factory").glob("*.json"),
            *(release_root / "metadata").glob("*.json"),
        ]
    ):
        _reject_control_keys(_read_json_object(path), label=path.name)
    return repeat_names_by_anchor


def _close(left: float, right: float, *, tolerance: float = 0.0021) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=tolerance)


def _runtime_port_signature(
    row_id: str,
    signature: Any,
    runtime: Mapping[str, Any],
) -> None:
    ports = runtime["ports"]
    if isinstance(signature, str):
        lowered = signature.lower()
        if lowered in {"none", "0"}:
            expected_count = 0
        else:
            pieces = lowered.split("x")
            try:
                expected_count = (
                    int(pieces[0]) + int(pieces[1]) if len(pieces) == 2 else None
                )
            except ValueError:
                expected_count = None
        if expected_count is None:
            raise DepthValidationError(f"{row_id}: unrecognized legacy port signature")
        if expected_count != len(ports):
            raise DepthValidationError(f"{row_id}: runtime port count differs")
        return
    if not isinstance(signature, Mapping):
        raise DepthValidationError(f"{row_id}: malformed port signature")
    # Frozen core-v1 uses an empty object when a curriculum row did not declare
    # a port contract. It means "unspecified", not "expect zero"; controlled
    # depth rows always carry the complete count/names/geometry witness below.
    if not signature:
        return
    if signature.get("count") != len(ports):
        raise DepthValidationError(f"{row_id}: runtime port count differs")
    names = signature.get("names")
    if isinstance(names, list) and list(names) != [str(port["name"]) for port in ports]:
        raise DepthValidationError(f"{row_id}: runtime port names differ")
    expected_ports = signature.get("ports")
    if not isinstance(expected_ports, list):
        return
    if len(expected_ports) != len(ports):
        raise DepthValidationError(f"{row_id}: runtime port records differ")
    for expected, observed in zip(expected_ports, ports, strict=True):
        if not isinstance(expected, dict):
            raise DepthValidationError(f"{row_id}: malformed port record")
        if (
            str(expected.get("name")) != str(observed["name"])
            or not _close(float(expected.get("width", -1)), float(observed["width"]))
            or not _close(
                float(expected.get("orientation", -1000)),
                float(observed["orientation"]),
                tolerance=1e-6,
            )
        ):
            raise DepthValidationError(f"{row_id}: runtime port record differs")
        center = expected.get("center")
        if (
            not isinstance(center, list)
            or len(center) != 2
            or any(
                not _close(float(left), float(right))
                for left, right in zip(center, observed["center"], strict=True)
            )
        ):
            raise DepthValidationError(f"{row_id}: runtime port center differs")


def _changes_repeat_count(
    row: Mapping[str, Any],
    repeat_names_by_anchor: Mapping[str, set[str]],
) -> bool:
    parent_id = str(row["parent_core_id"])
    return bool(
        set(map(str, row["controlled_axes"]))
        & repeat_names_by_anchor.get(parent_id, set())
    )


def _validate_repeated_element_counts(
    rows: Sequence[Mapping[str, Any]],
    repeat_names_by_anchor: Mapping[str, set[str]],
) -> None:
    """Bind every changed repeat-count literal to emitted polygon evidence."""

    for row in rows:
        if int(row["realization_slot"]) <= 0 or not _changes_repeat_count(
            row,
            repeat_names_by_anchor,
        ):
            continue
        row_id = str(row["id"])
        repeat_names = repeat_names_by_anchor[str(row["parent_core_id"])]
        values = _literal_map(str(row["code"]))
        counts: dict[str, int] = {}
        for name in sorted(repeat_names):
            value = values.get(name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise DepthValidationError(
                    f"{row_id}: {name} repeat count is not a positive integer"
                )
            counts[name] = value
        expected = math.prod(counts.values())
        evidence = _json_object(
            row_id,
            "verification_evidence_json",
            row["verification_evidence_json"],
        )
        metrics = evidence.get("runtime_structural_metrics")
        observed = (
            metrics.get("polygon_count") if isinstance(metrics, Mapping) else None
        )
        if (
            isinstance(observed, bool)
            or not isinstance(observed, int)
            or observed != expected
        ):
            raise DepthValidationError(
                f"{row_id}: repeat-count geometry witness differs: "
                f"counts={counts}, expected_polygons={expected}, "
                f"observed_polygons={observed!r}"
            )


def _validate_runtime_port_evidence(
    row_id: str,
    evidence: Mapping[str, Any],
    port_gate: Any,
) -> None:
    if evidence.get("port_count") != port_gate.port_count:
        raise DepthValidationError(f"{row_id}: runtime port evidence differs")
    if (
        evidence.get("port_orientation_side_histogram")
        != port_gate.orientation_side_histogram
    ):
        raise DepthValidationError(f"{row_id}: runtime port histogram differs")
    expected_witnesses = [asdict(witness) for witness in port_gate.witnesses]
    if evidence.get("port_witnesses") != expected_witnesses:
        raise DepthValidationError(f"{row_id}: runtime port witnesses differ")


def _execute_rows(
    rows: Sequence[Mapping[str, Any]],
    anchors: Mapping[str, Mapping[str, Any]],
    repeat_names_by_anchor: Mapping[str, set[str]],
) -> None:
    runtimes: dict[str, dict[str, Any]] = {}

    def runtime_for(row: Mapping[str, Any]) -> dict[str, Any]:
        digest = str(row["code_sha256"])
        if digest not in runtimes:
            runtimes[digest] = execute_program(
                str(row["code"]),
                isolation="in_process",
            )
        return runtimes[digest]

    for index, row in enumerate(rows, start=1):
        row_id = str(row["id"])
        runtime = runtime_for(row)
        spans = runtime["bbox_span_um"]
        if any(
            not _close(float(expected), float(observed))
            for expected, observed in zip(row["footprint_um"], spans, strict=True)
        ):
            raise DepthValidationError(f"{row_id}: runtime footprint differs")
        signature = _json_value(
            row_id,
            "port_signature_json",
            row["port_signature_json"],
        )
        _runtime_port_signature(row_id, signature, runtime)

        if int(row["realization_slot"]) > 0:
            parent_id = str(row["parent_core_id"])
            anchor = anchors[parent_id]
            anchor_runtime = runtime_for(anchor)
            changes_repeat_count = _changes_repeat_count(
                row,
                repeat_names_by_anchor,
            )
            report = validate_candidate(
                anchor_runtime,
                runtime,
                minimum_changed_fraction=0.002,
                maximum_changed_fraction=1.0,
                require_same_connected_components=not changes_repeat_count,
                require_same_holes=not changes_repeat_count,
                require_bbox_edge_ports=str(row["level"]) == "L4",
            )
            if not report.passed:
                raise DepthValidationError(
                    f"{row_id}: runtime candidate gate failed: {report.errors}"
                )
            evidence = _json_object(
                row_id,
                "verification_evidence_json",
                row["verification_evidence_json"],
            )
            if evidence.get("runtime_structural_metrics") != runtime.get(
                "structural_metrics"
            ):
                raise DepthValidationError(
                    f"{row_id}: runtime structural evidence differs"
                )
            if evidence.get("mask_delta") != asdict(report.mask_delta):
                raise DepthValidationError(f"{row_id}: runtime mask evidence differs")
            anchor_footprint = tuple(
                float(value) for value in anchor_runtime["bbox_span_um"]
            )
            candidate_footprint = tuple(
                float(value) for value in runtime["bbox_span_um"]
            )
            footprint_changed = any(
                not math.isclose(before, after, rel_tol=0.0, abs_tol=1e-9)
                for before, after in zip(
                    anchor_footprint,
                    candidate_footprint,
                    strict=True,
                )
            )
            normalized_changed_fraction: float | None = None
            if not footprint_changed:
                normalized_changed_fraction = mask_delta(
                    render_geometry(
                        anchor_runtime,
                        mode="maximum_visibility",
                    ).png_bytes,
                    render_geometry(
                        runtime,
                        mode="maximum_visibility",
                    ).png_bytes,
                ).changed_fraction
                if normalized_changed_fraction < 0.002:
                    raise DepthValidationError(
                        f"{row_id}: model input has no visible signal"
                    )
            if evidence.get("model_input_signal") != {
                "footprint_changed": footprint_changed,
                "normalized_changed_fraction": normalized_changed_fraction,
            }:
                raise DepthValidationError(
                    f"{row_id}: model-input evidence differs"
                )
            _validate_runtime_port_evidence(row_id, evidence, report.port_gate)
            views = render_views(runtime)
            if (
                sha256_bytes(views["maximum_visibility"].png_bytes)
                != row["image_sha256"]
                or sha256_bytes(views["physical_aspect"].png_bytes)
                != row["target_image_sha256"]
            ):
                raise DepthValidationError(
                    f"{row_id}: runtime render differs from embedded image"
                )
        if index % 100 == 0 or index == len(rows):
            print(
                f"depth-v1 execution: {index}/{len(rows)} programs checked",
                flush=True,
            )


def validate_release(
    release_root: Path,
    dataset_root: Path,
    *,
    execute_programs: bool = False,
) -> dict[str, Any]:
    release_root = release_root.expanduser().resolve()
    dataset_root = dataset_root.expanduser().resolve()
    if not release_root.is_dir():
        raise DepthValidationError(f"depth release root is missing: {release_root}")
    if not dataset_root.is_dir():
        raise DepthValidationError(f"dataset root is missing: {dataset_root}")

    try:
        verify_checksums(release_root)
    except DepthSchemaError as exc:
        raise DepthValidationError(str(exc)) from exc
    manifest = _read_json_object(release_root / "metadata" / "manifest.json")
    expected_parent_digest = str(manifest.get("parent_core_digest_sha256", ""))
    core_rows, _core_freeze = _load_frozen_core(
        dataset_root,
        expected_digest=expected_parent_digest,
    )
    rows, rows_by_split = _load_depth_shards(release_root, manifest)
    for row in rows:
        _validate_row_static(row)
    _validate_frozen_logical_release(manifest, rows)
    try:
        population = validate_depth_population(
            rows,
            expected_parent_core_digest_sha256=expected_parent_digest,
        )
    except DepthSchemaError as exc:
        raise DepthValidationError(str(exc)) from exc
    for split, split_rows in rows_by_split.items():
        for row in split_rows:
            expected = (
                "train"
                if int(row["realization_slot"]) in {-1, 0, 1, 2, 3, 4, 5}
                else "validation"
            )
            if split != expected:
                raise DepthValidationError(
                    f"{row['id']}: stored in {split}, expected {expected}"
                )

    anchors = _validate_core_relationships(rows, core_rows)
    repeat_names_by_anchor = _verify_freeze_and_manifests(
        release_root,
        dataset_root,
        manifest,
        rows,
        anchors,
    )
    _validate_repeated_element_counts(rows, repeat_names_by_anchor)
    if execute_programs:
        _execute_rows(rows, anchors, repeat_names_by_anchor)

    return {
        **population,
        "checksums_verified": True,
        "core_payloads_verified": CORE_ROW_COUNT,
        "executed_programs": len(rows) if execute_programs else 0,
        "logical_release_sha256": manifest["logical_release_sha256"],
        "manifest_verified": True,
        "shard_count": len(manifest["shards"]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release-root",
        type=Path,
        default=DEPTH_ROOT,
        help="Built depth-v1 release root.",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=DATASET_ROOT,
        help="PixCell dataset root containing frozen core-v1.",
    )
    parser.add_argument(
        "--execute-programs",
        action="store_true",
        help="Execute all programs and recheck runtime/raster evidence.",
    )
    args = parser.parse_args()
    report = validate_release(
        args.release_root,
        args.dataset_root,
        execute_programs=args.execute_programs,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
