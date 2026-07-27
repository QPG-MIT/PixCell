#!/usr/bin/env python3
"""Build PixCell depth-v1 from the immutable core-v1 Parquet release.

The builder changes no core-v1 artifact. It takes the unique semantic row for
each approved grammar as an anchor, discovers safe model-visible parameter
axes by execution, emits the fixed r01-r07 schedule where such an axis exists,
and publishes only descendants that pass the source, runtime, port,
structural, and causal-signal gates.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import io
import json
import math
import os
import shutil
import sys
import tempfile
import time
import warnings
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import pyarrow.parquet as pq
from datasets import Dataset
from datasets.utils.logging import disable_progress_bar
from PIL import Image


SCRIPT_ROOT = Path(__file__).resolve().parent
DEPTH_ROOT = SCRIPT_ROOT.parent
DATASET_ROOT = DEPTH_ROOT.parent
CORE_SCRIPTS = DATASET_ROOT / "scripts"
sys.path.insert(0, str(CORE_SCRIPTS))
sys.path.insert(0, str(SCRIPT_ROOT))

from _shared import (  # noqa: E402
    LEVELS,
    ReleaseError,
    canonical_json,
    forbidden_release_imports,
    normalized_d4_sha256,
    primitive_calls,
    purity_violations,
    sha256_bytes,
    sha256_file,
    top_level_parameters,
)
from contracts import (  # noqa: E402
    CandidateSpec,
    ParameterAxis,
    ParameterClass,
    ParameterContract,
    candidate_specs,
    classify_parameters,
    normalized_grammar_hash,
    rewrite_parameters,
    top_level_literals,
)
from render_galleries import render_galleries  # noqa: E402
from runtime import (  # noqa: E402
    CandidateGateReport,
    RuntimeGateError,
    derive_optical_port_specs,
    execute_program,
    gate_ports,
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
    FROZEN_LOGICAL_RELEASE_SHA256,
    bind_logical_row_sha256,
    build_freeze,
    build_manifest,
    canonical_sha256,
    depth_features,
    plan_shards,
    sha256_file as depth_sha256_file,
    validate_depth_population,
    write_checksums,
    write_json,
)


CORE_DIGEST = "e1c509dca337ce485efcb2b35101a052e06b12331b63a2f21a36c93b3682ea89"
CORE_GRAMMAR_CATALOG_SHA256 = (
    "2b833651a688c9cd33b3fcc5f4b79fd45307b2a28060a583ef9a1464eb8d89a1"
)
GENERATOR_VERSION = "pixcell-depth-v1-builder-1"
MAX_ROWS_PER_SHARD = 512
GENERATED_DIRECTORIES = ("data", "factory", "galleries", "metadata")
SPLIT_BY_SLOT = {
    **{slot: "train" for slot in range(0, 6)},
    **{slot: "validation" for slot in range(6, 8)},
}
warnings.filterwarnings(
    "ignore",
    message=r"bend_euler angle should be 90 or 180.*",
    category=UserWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r"\{.*\} ignored for cross_section .*",
    category=UserWarning,
)


class DepthBuildError(RuntimeError):
    """Raised when the frozen depth schedule cannot be produced honestly."""


@dataclass(frozen=True)
class _MaterializationSuccess:
    """One gate-clean candidate cached within a single anchor preparation."""

    updates: tuple[tuple[str, int | float], ...]
    code: str
    runtime: dict[str, Any]
    report: CandidateGateReport
    source_evidence: dict[str, Any]
    derived_ports: bool


@dataclass(frozen=True)
class _MaterializationFailure:
    """A deterministic candidate failure cached to avoid repeating execution."""

    detail: str


_MaterializationOutcome = _MaterializationSuccess | _MaterializationFailure
_MaterializationCache = dict[tuple[str, bool], _MaterializationOutcome]


@dataclass(frozen=True)
class _QualificationFailure:
    """One aggregate qualification finding for a semantic anchor."""

    anchor_id: str
    grammar_id: str
    stage: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class _PreparedAnchor:
    """All-or-nothing result of preparing one anchor's depth schedule."""

    anchor_id: str
    grammar_id: str
    contract_record: dict[str, Any] | None
    plan_record: dict[str, Any] | None
    descendants: tuple[dict[str, Any], ...]
    outcome: str
    failure: _QualificationFailure | None = None

    def __post_init__(self) -> None:
        if self.outcome == "complete":
            if len(self.descendants) != 7:
                raise ValueError(
                    f"{self.anchor_id}: complete preparation must have seven rows"
                )
            if self.contract_record is None or self.plan_record is None:
                raise ValueError(
                    f"{self.anchor_id}: complete preparation lacks release records"
                )
            return
        if self.outcome not in {"anchor_only", "fatal"}:
            raise ValueError(f"{self.anchor_id}: unknown preparation outcome")
        if self.descendants:
            raise ValueError(
                f"{self.anchor_id}: incomplete preparation retained partial rows"
            )
        if self.failure is None:
            raise ValueError(
                f"{self.anchor_id}: incomplete preparation lacks a failure"
            )
        if self.outcome == "anchor_only":
            if self.contract_record is None or self.plan_record is None:
                raise ValueError(
                    f"{self.anchor_id}: anchor-only preparation lacks release records"
                )
        elif self.contract_record is not None or self.plan_record is not None:
            raise ValueError(
                f"{self.anchor_id}: fatal preparation retained release records"
            )


def _hash_id(prefix: str, *values: str) -> str:
    payload = "\0".join(values).encode("utf-8")
    return f"{prefix}_{hashlib.sha256(payload).hexdigest()[:24]}"


def _core_paths(dataset_root: Path) -> list[Path]:
    paths: list[Path] = []
    for level in LEVELS:
        matches = sorted((dataset_root / "data" / level).glob("train-*.parquet"))
        if len(matches) != 1:
            raise DepthBuildError(
                f"{level}: expected one frozen core Parquet shard, got {len(matches)}"
            )
        paths.append(matches[0])
    return paths


def _load_core(dataset_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    freeze_path = dataset_root / "factory" / "core-v1" / "freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("release_digest_sha256") != CORE_DIGEST:
        raise DepthBuildError("core-v1 logical digest differs from depth-v1 binding")
    grammar_path = dataset_root / "factory" / "core-v1" / "grammar_catalog.json"
    if sha256_file(grammar_path) != CORE_GRAMMAR_CATALOG_SHA256:
        raise DepthBuildError("core-v1 grammar catalog differs from depth-v1 binding")
    references = freeze.get("reference_artifacts")
    if not isinstance(references, dict) or not references:
        raise DepthBuildError("core-v1 freeze has no reference artifact map")
    for relative, expected in sorted(references.items()):
        path = dataset_root / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise DepthBuildError(f"frozen core-v1 artifact drift: {relative}")

    rows: list[dict[str, Any]] = []
    for path in _core_paths(dataset_root):
        table = pq.read_table(path)
        if tuple(table.schema.names) != CORE_ROW_COLUMNS:
            raise DepthBuildError(f"core schema drift: {path.relative_to(dataset_root)}")
        rows.extend(table.to_pylist())
    if len(rows) != CORE_ROW_COUNT:
        raise DepthBuildError(f"core row count {len(rows)} != {CORE_ROW_COUNT}")
    if len({str(row["id"]) for row in rows}) != len(rows):
        raise DepthBuildError("core row IDs are not unique")
    return rows, freeze


def _core_snapshot(
    dataset_root: Path,
    freeze: Mapping[str, Any],
) -> dict[str, str]:
    references = freeze["reference_artifacts"]
    return {
        relative: sha256_file(dataset_root / relative)
        for relative in sorted(references)
    }


def _path_contains(ancestor: Path, descendant: Path) -> bool:
    return ancestor == descendant or ancestor in descendant.parents


def _protected_core_roots(
    dataset_root: Path,
    freeze: Mapping[str, Any],
) -> tuple[Path, ...]:
    references = freeze.get("reference_artifacts")
    if not isinstance(references, dict) or not references:
        raise DepthBuildError("core-v1 freeze has no reference artifact map")
    roots = {dataset_root / "factory" / "core-v1"}
    for relative in references:
        raw = Path(str(relative))
        if not raw.parts or raw.is_absolute() or ".." in raw.parts:
            raise DepthBuildError(
                f"core-v1 freeze has an unsafe reference path: {relative!r}"
            )
        roots.add(dataset_root / raw.parts[0])
    return tuple(sorted((path.resolve() for path in roots), key=str))


def _assert_safe_output_path(
    dataset_root: Path,
    output: Path,
    freeze: Mapping[str, Any],
) -> None:
    """Keep depth output disjoint from every frozen core subtree."""

    resolved_dataset = dataset_root.expanduser().resolve()
    resolved_output = output.expanduser().resolve()
    if _path_contains(resolved_output, resolved_dataset):
        raise DepthBuildError(
            "depth output cannot equal or contain the parent dataset root"
        )
    conflicts = [
        root
        for root in _protected_core_roots(resolved_dataset, freeze)
        if _path_contains(root, resolved_output)
        or _path_contains(resolved_output, root)
    ]
    if conflicts:
        relative_conflicts = [
            (
                path.relative_to(resolved_dataset).as_posix()
                if _path_contains(resolved_dataset, path)
                else str(path)
            )
            for path in conflicts
        ]
        raise DepthBuildError(
            "depth output overlaps frozen core/reference roots: "
            + ", ".join(relative_conflicts)
        )


def _semantic_anchors(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["grammar_id"])].append(row)
    anchors: list[dict[str, Any]] = []
    by_grammar: dict[str, dict[str, Any]] = {}
    for grammar_id, members in sorted(grouped.items()):
        semantic = [row for row in members if row["variation_role"] == "semantic"]
        if len(semantic) != 1:
            raise DepthBuildError(
                f"{grammar_id}: expected one semantic anchor, got {len(semantic)}"
            )
        anchor = dict(semantic[0])
        anchors.append(anchor)
        by_grammar[grammar_id] = anchor
    if len(anchors) != 547:
        raise DepthBuildError(f"semantic anchor count {len(anchors)} != 547")
    anchors.sort(key=lambda row: (str(row["level"]), str(row["id"])))
    return anchors, by_grammar


def _literal_map(code: str) -> dict[str, Any]:
    return {item.name: item.value for item in top_level_literals(code)}


class _LiteralRewriter(ast.NodeTransformer):
    def __init__(self, updates: Mapping[str, Any]) -> None:
        self.updates = dict(updates)
        self.rewritten: set[str] = set()

    def visit_Module(self, node: ast.Module) -> ast.Module:  # noqa: N802
        rewritten: list[ast.stmt] = []
        for child in node.body:
            if isinstance(child, (ast.Assign, ast.AnnAssign)):
                targets = (
                    child.targets if isinstance(child, ast.Assign) else [child.target]
                )
                if len(targets) == 1 and isinstance(targets[0], ast.Name):
                    name = targets[0].id
                    if name in self.updates:
                        expression = ast.parse(
                            repr(self.updates[name]),
                            mode="eval",
                        ).body
                        child.value = ast.copy_location(expression, child.value)
                        self.rewritten.add(name)
            rewritten.append(child)
        node.body = rewritten
        return node


def _rewrite_literals(code: str, updates: Mapping[str, Any]) -> str:
    transformer = _LiteralRewriter(updates)
    tree = transformer.visit(ast.parse(code))
    if transformer.rewritten != set(updates):
        missing = sorted(set(updates) - transformer.rewritten)
        raise DepthBuildError(f"literal update targets are absent: {missing}")
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n"


def _source_gate(
    anchor_code: str,
    candidate_code: str,
    *,
    expected_changed: set[str],
) -> dict[str, Any]:
    try:
        compile(candidate_code, "<pixcell-depth-candidate>", "exec")
    except SyntaxError as exc:
        raise DepthBuildError(f"candidate does not compile: {exc}") from exc
    violations = purity_violations(candidate_code)
    if violations:
        raise DepthBuildError(f"candidate purity violations: {violations}")
    forbidden = forbidden_release_imports(candidate_code)
    if forbidden:
        raise DepthBuildError(f"candidate imports forbidden packages: {forbidden}")
    before = _literal_map(anchor_code)
    after = _literal_map(candidate_code)
    if before.keys() != after.keys():
        raise DepthBuildError("top-level literal set changed")
    observed_changed = {name for name in before if before[name] != after[name]}
    if observed_changed != expected_changed:
        raise DepthBuildError(
            "candidate literal delta differs from contract: "
            f"observed={sorted(observed_changed)} "
            f"expected={sorted(expected_changed)}"
        )
    before_hash = normalized_grammar_hash(anchor_code)
    after_hash = normalized_grammar_hash(candidate_code)
    if before_hash != after_hash:
        raise DepthBuildError("normalized source grammar changed")
    if primitive_calls(anchor_code) != primitive_calls(candidate_code):
        raise DepthBuildError("primitive API set changed")
    return {
        "changed_literals": sorted(observed_changed),
        "normalized_grammar_hash": before_hash,
    }


def _shape_axis_pair(left: str, right: str) -> bool:
    pair = {left.lower(), right.lower()}
    if pair == {"length_um", "width_um"}:
        return True
    for x_suffix, y_suffix in (
        ("_x_um", "_y_um"),
        ("_x", "_y"),
    ):
        if left.lower().endswith(x_suffix) and right.lower().endswith(y_suffix):
            return left.lower()[: -len(x_suffix)] == right.lower()[: -len(y_suffix)]
        if right.lower().endswith(x_suffix) and left.lower().endswith(y_suffix):
            return right.lower()[: -len(x_suffix)] == left.lower()[: -len(y_suffix)]
    return False


def _coalesce_equal_shape_axes(
    contract: ParameterContract,
) -> ParameterContract:
    values = {item.name: item.value for item in contract.assignments}
    axes = list(contract.axes)
    consumed: set[int] = set()
    merged: list[ParameterAxis] = []
    for index, axis in enumerate(axes):
        if index in consumed:
            continue
        members = [axis]
        consumed.add(index)
        changed = True
        while changed:
            changed = False
            names = [name for item in members for name in item.names]
            for other_index, other in enumerate(axes):
                if other_index in consumed:
                    continue
                if any(
                    _shape_axis_pair(left, right)
                    and math.isclose(
                        float(values[left]),
                        float(values[right]),
                        rel_tol=0.0,
                        abs_tol=1e-9,
                    )
                    for left in names
                    for right in other.names
                ):
                    members.append(other)
                    consumed.add(other_index)
                    changed = True
        if len(members) == 1:
            merged.append(axis)
            continue
        names = tuple(sorted({name for item in members for name in item.names}))
        merged.append(
            ParameterAxis(
                axis_id="axis:equal:" + "+".join(names),
                names=names,
                parameter_class=axis.parameter_class,
                priority=max(item.priority for item in members) + 1,
                dependency_kind="equal_shape_axes",
            )
        )
    merged.sort(key=lambda item: (-item.priority, item.axis_id))
    return replace(contract, axes=tuple(merged))


def _semantic_relation_errors(
    anchor_code: str,
    candidate_code: str,
) -> list[str]:
    before = _literal_map(anchor_code)
    after = _literal_map(candidate_code)
    names = sorted(
        name
        for name, value in before.items()
        if name.endswith("_um")
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
        and float(value) > 0
    )
    errors: list[str] = []
    for index, left in enumerate(names):
        for right in names[index + 1 :]:
            before_left = float(before[left])
            before_right = float(before[right])
            after_left = float(after[left])
            after_right = float(after[right])
            if _shape_axis_pair(left, right) and math.isclose(
                before_left,
                before_right,
                rel_tol=0.0,
                abs_tol=1e-9,
            ):
                if not math.isclose(
                    after_left,
                    after_right,
                    rel_tol=0.0,
                    abs_tol=1e-7,
                ):
                    errors.append(f"equal shape axes separated: {left}, {right}")
    return errors


def _port_signature(runtime: Mapping[str, Any]) -> dict[str, Any]:
    ports = [
        {
            "center": [float(value) for value in port["center"]],
            "name": str(port["name"]),
            "orientation": float(port["orientation"]),
            "width": float(port["width"]),
        }
        for port in runtime["ports"]
    ]
    return {
        "count": len(ports),
        "names": [port["name"] for port in ports],
        "ports": ports,
    }


def _candidate_topology(runtime: Mapping[str, Any]) -> dict[str, Any]:
    intervals = runtime.get("edge_material_intervals", {})
    return {
        "edge_material_interval_counts": {
            side: len(values) for side, values in sorted(intervals.items())
        },
        "port_signature": _port_signature(runtime),
        "runtime_structural_metrics": runtime["structural_metrics"],
    }


def _parameter_payload(
    anchor: Mapping[str, Any],
    candidate_code: str,
) -> dict[str, Any]:
    """Preserve the core parameter contract while updating live values."""

    try:
        payload = copy.deepcopy(json.loads(str(anchor["parameters_json"])))
    except (TypeError, json.JSONDecodeError) as exc:
        raise DepthBuildError(f"{anchor['id']}: malformed core parameters") from exc
    if set(payload) != {"fixed_context", "parameters"}:
        raise DepthBuildError(
            f"{anchor['id']}: unexpected core parameter payload keys"
        )
    parameters = payload.get("parameters")
    fixed_context = payload.get("fixed_context")
    if not isinstance(parameters, dict) or not isinstance(fixed_context, dict):
        raise DepthBuildError(
            f"{anchor['id']}: malformed core parameter payload sections"
        )
    live_values = top_level_parameters(candidate_code)
    missing = sorted(set(parameters) - set(live_values))
    if missing:
        raise DepthBuildError(
            f"{anchor['id']}: declared parameters absent from candidate: {missing}"
        )
    payload["parameters"] = {
        name: copy.deepcopy(live_values[name]) for name in parameters
    }
    return payload


def _interpolate_updates(
    anchor_values: Mapping[str, Any],
    target: Mapping[str, int | float],
    ratio: float,
) -> dict[str, int | float]:
    updates: dict[str, int | float] = {}
    for name, target_value in target.items():
        old_value = anchor_values[name]
        raw = float(old_value) + ratio * (float(target_value) - float(old_value))
        if isinstance(old_value, int) and not isinstance(old_value, bool):
            direction = 1 if float(target_value) >= float(old_value) else -1
            value = int(round(raw))
            if value == old_value:
                value = int(old_value) + direction
            updates[name] = max(1, value)
        else:
            value = (
                round(round(raw / 0.002) * 0.002, 6)
                if name.endswith("_um")
                else round(raw, 8)
            )
            if value == -0.0:
                value = 0.0
            updates[name] = value
    return updates


def _candidate_attempts(
    anchor_values: Mapping[str, Any],
    target: Mapping[str, int | float],
) -> list[dict[str, int | float]]:
    attempts: list[dict[str, int | float]] = []
    seen: set[str] = set()
    for ratio in (
        1.0,
        0.75,
        0.50,
        0.35,
        0.25,
        0.15,
        1.25,
        1.50,
        2.00,
        3.00,
        4.00,
        -0.15,
        -0.25,
        -0.35,
        -0.50,
        -0.75,
        -1.00,
        -2.00,
        -3.00,
        -4.00,
    ):
        updates = _interpolate_updates(anchor_values, target, ratio)
        key = canonical_json(updates)
        if key not in seen and any(anchor_values[name] != value for name, value in updates.items()):
            attempts.append(updates)
            seen.add(key)
    if target and all(
        isinstance(anchor_values[name], int)
        and not isinstance(anchor_values[name], bool)
        for name in target
    ):
        for step in (1, 2, 3, 4):
            updates = {}
            for name, target_value in target.items():
                old_value = int(anchor_values[name])
                if int(target_value) > old_value:
                    direction = 1
                elif int(target_value) < old_value:
                    direction = -1
                else:
                    direction = 1
                updates[name] = max(2, old_value + direction * step)
            key = canonical_json(updates)
            if key not in seen and any(
                anchor_values[name] != value for name, value in updates.items()
            ):
                attempts.append(updates)
                seen.add(key)
    return attempts


def _materialize(
    anchor: Mapping[str, Any],
    anchor_runtime: Mapping[str, Any],
    updates: Mapping[str, int | float],
    *,
    allow_component_count_change: bool = False,
    anchor_model_png: bytes | None = None,
) -> tuple[str, dict[str, Any], CandidateGateReport, dict[str, Any], bool]:
    anchor_code = str(anchor["code"])
    code = rewrite_parameters(anchor_code, updates)
    relation_errors = _semantic_relation_errors(anchor_code, code)
    if relation_errors:
        raise DepthBuildError("; ".join(relation_errors))
    derived_ports = "optical_port_specs" in _literal_map(anchor_code)
    derived_updates: dict[str, Any] = {}
    if derived_ports:
        initial_runtime = execute_program(code, isolation="in_process")
        specs = derive_optical_port_specs(anchor_runtime, initial_runtime)
        derived_updates["optical_port_specs"] = specs
        code = _rewrite_literals(code, derived_updates)
    expected_changed = set(updates)
    for name, value in derived_updates.items():
        if _literal_map(anchor_code)[name] != value:
            expected_changed.add(name)
    source_evidence = _source_gate(
        anchor_code,
        code,
        expected_changed=expected_changed,
    )
    runtime = execute_program(code, isolation="in_process")
    report = validate_candidate(
        anchor_runtime,
        runtime,
        minimum_changed_fraction=0.002,
        maximum_changed_fraction=1.0,
        require_same_connected_components=not allow_component_count_change,
        require_same_holes=not allow_component_count_change,
        require_bbox_edge_ports=str(anchor["level"]) == "L4",
    )
    if not report.passed:
        raise DepthBuildError("; ".join(report.errors))
    before_footprint = tuple(float(value) for value in anchor_runtime["bbox_span_um"])
    after_footprint = tuple(float(value) for value in runtime["bbox_span_um"])
    footprint_changed = any(
        not math.isclose(before, after, rel_tol=0.0, abs_tol=1e-9)
        for before, after in zip(before_footprint, after_footprint, strict=True)
    )
    normalized_input_delta: float | None = None
    if not footprint_changed:
        if anchor_model_png is None:
            anchor_model_png = render_geometry(
                anchor_runtime,
                mode="maximum_visibility",
            ).png_bytes
        candidate_model_png = render_geometry(
            runtime,
            mode="maximum_visibility",
        ).png_bytes
        normalized_input_delta = mask_delta(
            anchor_model_png,
            candidate_model_png,
        ).changed_fraction
        if normalized_input_delta < 0.002:
            raise DepthBuildError(
                "candidate has no observable model-input change: "
                f"normalized_changed_fraction={normalized_input_delta:.6f}"
            )
    source_evidence["model_input_signal"] = {
        "footprint_changed": footprint_changed,
        "normalized_changed_fraction": normalized_input_delta,
    }
    return code, runtime, report, source_evidence, derived_ports


def _validate_repeated_element_count(
    code: str,
    runtime: Mapping[str, Any],
    repeat_names: set[str],
) -> None:
    """Bind repeat-count literals to emitted material polygons."""

    values = _literal_map(code)
    counts: dict[str, int] = {}
    for name in sorted(repeat_names):
        value = values.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise DepthBuildError(f"{name}: repeat count is not a positive integer")
        counts[name] = value
    expected = math.prod(counts.values())
    metrics = runtime.get("structural_metrics")
    observed = metrics.get("polygon_count") if isinstance(metrics, Mapping) else None
    if (
        isinstance(observed, bool)
        or not isinstance(observed, int)
        or observed != expected
    ):
        raise DepthBuildError(
            "repeat-count geometry witness differs: "
            f"counts={counts}, expected_polygons={expected}, "
            f"observed_polygons={observed!r}"
        )


def _cached_materialization(
    anchor: Mapping[str, Any],
    anchor_runtime: Mapping[str, Any],
    updates: Mapping[str, int | float],
    *,
    allow_component_count_change: bool,
    anchor_model_png: bytes,
    cache: _MaterializationCache,
) -> _MaterializationOutcome:
    """Materialize one exact update at most once within an anchor build."""

    normalized_updates = {
        name: value for name, value in sorted(updates.items())
    }
    key = (
        canonical_json(normalized_updates),
        allow_component_count_change,
    )
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        code, runtime, report, source, derived = _materialize(
            anchor,
            anchor_runtime,
            normalized_updates,
            allow_component_count_change=allow_component_count_change,
            anchor_model_png=anchor_model_png,
        )
    except (DepthBuildError, RuntimeGateError, ReleaseError, ValueError) as exc:
        outcome: _MaterializationOutcome = _MaterializationFailure(str(exc))
    else:
        outcome = _MaterializationSuccess(
            updates=tuple(normalized_updates.items()),
            code=code,
            runtime=runtime,
            report=report,
            source_evidence=source,
            derived_ports=derived,
        )
    cache[key] = outcome
    return outcome


def _try_materialize(
    anchor: Mapping[str, Any],
    anchor_runtime: Mapping[str, Any],
    target_updates: Mapping[str, int | float],
    *,
    allow_component_count_change: bool = False,
    anchor_model_png: bytes | None = None,
    cache: _MaterializationCache | None = None,
) -> tuple[
    dict[str, int | float],
    str,
    dict[str, Any],
    CandidateGateReport,
    dict[str, Any],
    bool,
]:
    anchor_values = _literal_map(str(anchor["code"]))
    if anchor_model_png is None:
        anchor_model_png = render_geometry(
            anchor_runtime,
            mode="maximum_visibility",
        ).png_bytes
    if cache is None:
        cache = {}
    errors: list[str] = []
    for updates in _candidate_attempts(anchor_values, target_updates):
        outcome = _cached_materialization(
            anchor,
            anchor_runtime,
            updates,
            allow_component_count_change=allow_component_count_change,
            anchor_model_png=anchor_model_png,
            cache=cache,
        )
        if isinstance(outcome, _MaterializationSuccess):
            effective_updates = dict(outcome.updates)
            return (
                effective_updates,
                outcome.code,
                outcome.runtime,
                outcome.report,
                outcome.source_evidence,
                outcome.derived_ports,
            )
        errors.append(outcome.detail)
    detail = errors[-1] if errors else "no nontrivial update was generated"
    raise DepthBuildError(detail)


def _qualify_axes(
    anchor: Mapping[str, Any],
    anchor_runtime: Mapping[str, Any],
    contract: ParameterContract,
    *,
    anchor_model_png: bytes,
    cache: _MaterializationCache,
) -> tuple[ParameterAxis, ...]:
    qualified: list[ParameterAxis] = []
    for axis in contract.axes:
        probe_contract = replace(contract, axes=(axis,))
        probes = candidate_specs(probe_contract)
        if not isinstance(probes, tuple):
            raise AssertionError("candidate_specs unexpectedly returned one item")
        low, high = probes[0], probes[1]
        try:
            _try_materialize(
                anchor,
                anchor_runtime,
                dict(low.updates),
                allow_component_count_change=(
                    axis.parameter_class
                    == ParameterClass.REPEAT_COUNT.value
                ),
                anchor_model_png=anchor_model_png,
                cache=cache,
            )
            _try_materialize(
                anchor,
                anchor_runtime,
                dict(high.updates),
                allow_component_count_change=(
                    axis.parameter_class
                    == ParameterClass.REPEAT_COUNT.value
                ),
                anchor_model_png=anchor_model_png,
                cache=cache,
            )
        except DepthBuildError:
            continue
        qualified.append(axis)
        if len(qualified) == 3:
            break
    if not qualified:
        raise DepthBuildError(f"{anchor['id']}: no runtime-safe parameter axis")
    return tuple(qualified)


def _instruction(
    footprint_um: Sequence[float],
    scale_px_per_um: Sequence[float],
) -> str:
    length_um, width_um = (float(value) for value in footprint_um)
    sx, sy = (float(value) for value in scale_px_per_um)
    reference = min(sx, sy)
    x_magnification = sx / reference
    y_magnification = sy / reference
    return (
        "The image is a device-only black-and-white silhouette: BLACK is "
        "material on layer (1,0), WHITE is background. "
        f"Footprint (bounding box): {length_um:.8g} x {width_um:.8g} micrometers. "
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


def _depth_common(
    anchor: Mapping[str, Any],
    *,
    slot: int,
    split_role: str,
) -> dict[str, Any]:
    grammar_id = str(anchor["grammar_id"])
    return {
        "depth_schema_version": DEPTH_SCHEMA_VERSION,
        "parent_core_id": str(anchor["id"]),
        "parent_code_sha256": str(anchor["code_sha256"]),
        "parent_core_digest_sha256": CORE_DIGEST,
        "geometry_id": _hash_id("dgeo", grammar_id, f"r{slot:02d}"),
        "realization_id": f"r{slot:02d}",
        "realization_slot": slot,
        "dependency_group": _hash_id("ddep", grammar_id),
        "split_role": split_role,
        "pose_id": "canonical",
        "render_id": "maximum_visibility",
        "depth_generator_version": GENERATOR_VERSION,
        "logical_row_sha256": "",
    }


def _wrap_core_row(
    row: Mapping[str, Any],
    anchor: Mapping[str, Any],
) -> dict[str, Any]:
    semantic = str(row["id"]) == str(anchor["id"])
    result = {column: copy.deepcopy(row[column]) for column in CORE_ROW_COLUMNS}
    if semantic:
        result.update(_depth_common(anchor, slot=0, split_role="train"))
        result.update(
            {
                "transform_kind": "anchor",
                "controlled_axes": [],
                "parameter_delta_json": "{}",
                "verification_evidence_json": canonical_json(
                    {
                        "core_code_sha256": row["code_sha256"],
                        "core_image_sha256": row["image_sha256"],
                        "core_target_image_sha256": row["target_image_sha256"],
                    }
                ),
            }
        )
    else:
        result.update(
            {
                "depth_schema_version": DEPTH_SCHEMA_VERSION,
                "parent_core_id": str(anchor["id"]),
                "parent_code_sha256": str(anchor["code_sha256"]),
                "parent_core_digest_sha256": CORE_DIGEST,
                "geometry_id": _hash_id("dextra", str(row["id"])),
                "realization_id": f"core-{row['variation_role']}",
                "realization_slot": -1,
                "transform_kind": f"core_{row['variation_role']}",
                "controlled_axes": [],
                "parameter_delta_json": "{}",
                "dependency_group": _hash_id("ddep", str(anchor["grammar_id"])),
                "split_role": "core-extra",
                "pose_id": (
                    "core-equivariance"
                    if row["variation_role"] == "equivariance"
                    else "canonical"
                ),
                "render_id": "core-maximum-visibility",
                "verification_evidence_json": canonical_json(
                    {
                        "core_code_sha256": row["code_sha256"],
                        "core_image_sha256": row["image_sha256"],
                        "core_target_image_sha256": row["target_image_sha256"],
                    }
                ),
                "depth_generator_version": GENERATOR_VERSION,
                "logical_row_sha256": "",
            }
        )
    result = {column: result[column] for column in DEPTH_ROW_COLUMNS}
    return bind_logical_row_sha256(result)


def _descendant_row(
    anchor: Mapping[str, Any],
    *,
    grammar_index: int,
    slot: int,
    spec: CandidateSpec,
    updates: Mapping[str, int | float],
    code: str,
    runtime: Mapping[str, Any],
    report: CandidateGateReport,
    source_evidence: Mapping[str, Any],
    derived_ports: bool,
) -> dict[str, Any]:
    views = render_views(runtime)
    model_view = views["maximum_visibility"]
    target_view = views["physical_aspect"]
    image_bytes = model_view.png_bytes
    target_bytes = target_view.png_bytes
    footprint = [float(value) for value in runtime["bbox_span_um"]]
    row_id = f"{anchor['id']}__depth_r{slot:02d}"
    anchor_values = _literal_map(str(anchor["code"]))
    directions: set[str] = set()
    for name, value in updates.items():
        before = float(anchor_values[name])
        after = float(value)
        if before != 0.0 and before * after > 0.0:
            directions.add("high" if abs(after) > abs(before) else "low")
        elif before * after < 0.0:
            directions.add("sign_flip")
        else:
            directions.add("high" if after > before else "low")
    effective_direction = (
        next(iter(directions)) if len(directions) == 1 else "mixed"
    )
    requested_updates = dict(spec.updates)
    delta = {
        "changes": {
            name: {"after": value, "before": anchor_values[name]}
            for name, value in sorted(updates.items())
        },
        "derived_updates": ["optical_port_specs"] if derived_ports else [],
        "effective_direction": effective_direction,
        "contract_fallback": bool(spec.fallback),
        "fallback_schedule": bool(
            spec.fallback or dict(updates) != requested_updates
        ),
        "runtime_fallback": dict(updates) != requested_updates,
        "requested_factors": {name: value for name, value in spec.factors},
        "requested_direction": spec.direction,
        "requested_updates": requested_updates,
        "role": spec.role,
    }
    port_report = report.port_gate
    verification = {
        "mask_delta": asdict(report.mask_delta),
        "model_input_signal": source_evidence["model_input_signal"],
        "normalized_grammar_hash": source_evidence["normalized_grammar_hash"],
        "port_count": port_report.port_count,
        "port_orientation_side_histogram": port_report.orientation_side_histogram,
        "port_witnesses": [asdict(item) for item in port_report.witnesses],
        "runtime_structural_metrics": runtime["structural_metrics"],
    }
    metadata = {
        "core_anchor_id": anchor["id"],
        "core_anchor_image_sha256": anchor["image_sha256"],
        "core_anchor_parameters_sha256": canonical_sha256(
            json.loads(str(anchor["parameters_json"]))
        ),
        "depth_realization": {
            "axis_ids": list(spec.axis_ids),
            "slot": f"r{slot:02d}",
        },
    }
    result = {column: copy.deepcopy(anchor[column]) for column in CORE_ROW_COLUMNS}
    result.update(
        {
            "id": row_id,
            "curriculum_order": CORE_ROW_COUNT + grammar_index * 7 + slot - 1,
            "image": {"bytes": image_bytes, "path": f"{row_id}.png"},
            "target_image": {
                "bytes": target_bytes,
                "path": f"{row_id}.target.png",
            },
            "code": code,
            "instruction": _instruction(footprint, model_view.scale_px_per_um),
            "leakage_group_id": str(anchor["leakage_group_id"]),
            "variation_role": "controlled_realization",
            "primitive_calls": primitive_calls(code),
            "port_signature_json": canonical_json(_port_signature(runtime)),
            "footprint_um": footprint,
            "parameters_json": canonical_json(_parameter_payload(anchor, code)),
            "topology_json": canonical_json(_candidate_topology(runtime)),
            "metadata_json": canonical_json(metadata),
            "image_sha256": sha256_bytes(image_bytes),
            "target_image_sha256": sha256_bytes(target_bytes),
            "code_sha256": sha256_bytes(code.encode("utf-8")),
            "normalized_d4_sha256": normalized_d4_sha256(
                Image.open(io.BytesIO(image_bytes))
            ),
            "view_policy": "maximum_visibility_depth_v1",
            "source_dataset_digest_sha256": CORE_DIGEST,
            "source_generator_version": GENERATOR_VERSION,
        }
    )
    result.update(_depth_common(anchor, slot=slot, split_role=SPLIT_BY_SLOT[slot]))
    result.update(
        {
            "transform_kind": f"{spec.role}_{effective_direction}",
            "controlled_axes": sorted(updates),
            "parameter_delta_json": canonical_json(delta),
            "verification_evidence_json": canonical_json(verification),
        }
    )
    result = {column: result[column] for column in DEPTH_ROW_COLUMNS}
    return bind_logical_row_sha256(result)


def _qualification_failure(
    anchor: Mapping[str, Any],
    *,
    stage: str,
    reason: str,
) -> _QualificationFailure:
    return _QualificationFailure(
        anchor_id=str(anchor["id"]),
        grammar_id=str(anchor["grammar_id"]),
        stage=stage,
        reason=reason,
    )


def _anchor_only_preparation(
    anchor: Mapping[str, Any],
    contract: ParameterContract,
    *,
    stage: str,
    reason: str,
) -> _PreparedAnchor:
    contract_record = contract.to_dict()
    contract_record["qualified_axis_ids"] = []
    return _PreparedAnchor(
        anchor_id=str(anchor["id"]),
        grammar_id=str(anchor["grammar_id"]),
        contract_record=contract_record,
        plan_record={
            "anchor_id": anchor["id"],
            "grammar_id": anchor["grammar_id"],
            "level": anchor["level"],
            "states": [],
        },
        descendants=(),
        outcome="anchor_only",
        failure=_qualification_failure(
            anchor,
            stage=stage,
            reason=reason,
        ),
    )


def _fatal_preparation(
    anchor: Mapping[str, Any],
    *,
    stage: str,
    reason: str,
) -> _PreparedAnchor:
    return _PreparedAnchor(
        anchor_id=str(anchor["id"]),
        grammar_id=str(anchor["grammar_id"]),
        contract_record=None,
        plan_record=None,
        descendants=(),
        outcome="fatal",
        failure=_qualification_failure(
            anchor,
            stage=stage,
            reason=reason,
        ),
    )


def _prepare_anchor(
    anchor: Mapping[str, Any],
    *,
    grammar_index: int,
) -> _PreparedAnchor:
    """Prepare one complete schedule without exposing partial descendants."""

    try:
        anchor_runtime = execute_program(str(anchor["code"]), isolation="in_process")
        anchor_model_png = render_geometry(
            anchor_runtime,
            mode="maximum_visibility",
        ).png_bytes
        anchor_ports = gate_ports(
            anchor_runtime,
            expected_count=len(anchor_runtime["ports"]),
            require_bbox_edge=str(anchor["level"]) == "L4",
        )
        if not anchor_ports.passed:
            raise DepthBuildError(
                f"{anchor['id']}: anchor port gate failed: {anchor_ports.errors}"
            )
    except (DepthBuildError, RuntimeGateError, ReleaseError, ValueError) as exc:
        return _fatal_preparation(
            anchor,
            stage="anchor_runtime",
            reason=str(exc),
        )
    try:
        contract = _coalesce_equal_shape_axes(
            classify_parameters(str(anchor["code"]), anchor)
        )
    except (DepthBuildError, RuntimeGateError, ReleaseError, ValueError) as exc:
        return _fatal_preparation(
            anchor,
            stage="parameter_contract",
            reason=str(exc),
        )
    cache: _MaterializationCache = {}
    try:
        qualified_axes = _qualify_axes(
            anchor,
            anchor_runtime,
            contract,
            anchor_model_png=anchor_model_png,
            cache=cache,
        )
    except DepthBuildError as exc:
        return _anchor_only_preparation(
            anchor,
            contract,
            stage="axis_qualification",
            reason=str(exc),
        )
    scheduled_contract = replace(contract, axes=qualified_axes)
    try:
        specs = candidate_specs(scheduled_contract)
    except (DepthBuildError, RuntimeGateError, ReleaseError, ValueError) as exc:
        return _fatal_preparation(
            anchor,
            stage="schedule_definition",
            reason=str(exc),
        )
    if not isinstance(specs, tuple) or len(specs) != 7:
        return _fatal_preparation(
            anchor,
            stage="schedule_definition",
            reason=f"{anchor['id']}: incomplete realization schedule",
        )
    repeat_names = {
        parameter.name
        for parameter in scheduled_contract.assignments
        if parameter.parameter_class == ParameterClass.REPEAT_COUNT.value
    }

    seen_parameter_states: set[str] = set()
    seen_model_inputs = {
        (str(anchor["image_sha256"]), str(anchor["instruction"]))
    }
    local_descendants: list[dict[str, Any]] = []
    selected: list[dict[str, Any]] = []
    for spec in specs:
        slot = int(spec.slot[1:])
        errors: list[str] = []
        accepted: tuple[dict[str, Any], dict[str, int | float]] | None = None
        for target in _candidate_attempts(
            _literal_map(str(anchor["code"])),
            dict(spec.updates),
        ):
            state_key = canonical_json(target)
            if state_key in seen_parameter_states:
                continue
            outcome = _cached_materialization(
                anchor,
                anchor_runtime,
                target,
                allow_component_count_change=bool(set(target) & repeat_names),
                anchor_model_png=anchor_model_png,
                cache=cache,
            )
            if isinstance(outcome, _MaterializationFailure):
                errors.append(outcome.detail)
                continue
            effective_updates = dict(outcome.updates)
            try:
                if set(effective_updates) & repeat_names:
                    _validate_repeated_element_count(
                        outcome.code,
                        outcome.runtime,
                        repeat_names,
                    )
                row = _descendant_row(
                    anchor,
                    grammar_index=grammar_index,
                    slot=slot,
                    spec=spec,
                    updates=effective_updates,
                    code=outcome.code,
                    runtime=outcome.runtime,
                    report=outcome.report,
                    source_evidence=outcome.source_evidence,
                    derived_ports=outcome.derived_ports,
                )
            except (
                DepthBuildError,
                RuntimeGateError,
                ReleaseError,
                ValueError,
            ) as exc:
                errors.append(str(exc))
                continue
            model_input_key = (
                str(row["image_sha256"]),
                str(row["instruction"]),
            )
            if model_input_key in seen_model_inputs:
                errors.append("model input duplicates an earlier realization")
                continue
            accepted = (row, effective_updates)
            seen_parameter_states.add(state_key)
            seen_model_inputs.add(model_input_key)
            break
        if accepted is None:
            detail = errors[-1] if errors else "all states duplicated earlier slots"
            return _anchor_only_preparation(
                anchor,
                contract,
                stage=f"schedule_{spec.slot}",
                reason=detail,
            )
        row, _ = accepted
        local_descendants.append(row)
        selected.append(
            {
                "axis_ids": list(spec.axis_ids),
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
        )

    contract_record = contract.to_dict()
    contract_record["qualified_axis_ids"] = [
        axis.axis_id for axis in qualified_axes
    ]
    return _PreparedAnchor(
        anchor_id=str(anchor["id"]),
        grammar_id=str(anchor["grammar_id"]),
        contract_record=contract_record,
        plan_record={
            "anchor_id": anchor["id"],
            "grammar_id": anchor["grammar_id"],
            "level": anchor["level"],
            "states": selected,
        },
        descendants=tuple(local_descendants),
        outcome="complete",
    )


def _prepare_all_anchors(
    anchors: Sequence[Mapping[str, Any]],
) -> list[_PreparedAnchor]:
    """Finish qualification for every anchor before enforcing the inventory."""

    prepared: list[_PreparedAnchor] = []
    started = time.monotonic()
    descendant_count = 0
    for grammar_index, anchor in enumerate(anchors):
        result = _prepare_anchor(anchor, grammar_index=grammar_index)
        prepared.append(result)
        descendant_count += len(result.descendants)
        if (grammar_index + 1) % 20 == 0 or grammar_index + 1 == len(anchors):
            elapsed = time.monotonic() - started
            print(
                f"depth-v1: qualified {grammar_index + 1}/{len(anchors)} anchors "
                f"({descendant_count} prepared descendants, {elapsed:.1f}s)",
                flush=True,
            )
    return prepared


def _assert_frozen_qualification_inventory(
    prepared: Sequence[_PreparedAnchor],
    *,
    expected_anchor_only: frozenset[str] = ANCHOR_ONLY_PARENT_IDS,
) -> None:
    """Require one exact, deterministic qualification outcome inventory."""

    if len(prepared) != APPROVED_REPRESENTATION_COUNT:
        raise DepthBuildError(
            "depth-v1 qualification barrier received "
            f"{len(prepared)} != {APPROVED_REPRESENTATION_COUNT} anchors"
        )
    by_id = {result.anchor_id: result for result in prepared}
    if len(by_id) != len(prepared):
        raise DepthBuildError("depth-v1 qualification barrier has repeated anchors")

    fatal = sorted(
        (
            result.failure.to_dict()
            for result in prepared
            if result.outcome == "fatal" and result.failure is not None
        ),
        key=lambda item: item["anchor_id"],
    )
    anchor_only = {
        result.anchor_id for result in prepared if result.outcome == "anchor_only"
    }
    complete = {
        result.anchor_id for result in prepared if result.outcome == "complete"
    }
    unexpected_anchor_only = sorted(anchor_only - expected_anchor_only)
    unexpectedly_complete = sorted(expected_anchor_only & complete)
    if fatal or unexpected_anchor_only or unexpectedly_complete:
        findings = sorted(
            (
                result.failure.to_dict()
                for result in prepared
                if result.outcome == "anchor_only" and result.failure is not None
            ),
            key=lambda item: item["anchor_id"],
        )
        raise DepthBuildError(
            "depth-v1 qualification inventory differs: "
            + canonical_json(
                {
                    "anchor_only_findings": findings,
                    "fatal": fatal,
                    "unexpected_anchor_only": unexpected_anchor_only,
                    "unexpectedly_complete": unexpectedly_complete,
                }
            )
        )


def _build_descendants(
    anchors: Sequence[Mapping[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    prepared = _prepare_all_anchors(anchors)
    _assert_frozen_qualification_inventory(prepared)

    descendants: list[dict[str, Any]] = []
    contract_records: list[dict[str, Any]] = []
    plan_records: list[dict[str, Any]] = []
    for result in prepared:
        if result.contract_record is None or result.plan_record is None:
            raise AssertionError("qualification barrier exposed a fatal result")
        descendants.extend(result.descendants)
        contract_records.append(result.contract_record)
        plan_records.append(result.plan_record)
    return descendants, contract_records, plan_records


def _ordered_rows(
    core_rows: Sequence[Mapping[str, Any]],
    descendants: Sequence[Mapping[str, Any]],
    anchors_by_grammar: Mapping[str, Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    wrapped = [
        _wrap_core_row(row, anchors_by_grammar[str(row["grammar_id"])])
        for row in core_rows
    ]
    train = [*wrapped, *(row for row in descendants if row["split_role"] == "train")]
    validation = [
        row for row in descendants if row["split_role"] == "validation"
    ]
    train.sort(
        key=lambda row: (
            0 if row["realization_slot"] in {-1, 0} else 1,
            int(row["curriculum_order"]),
            str(row["id"]),
        )
    )
    validation.sort(key=lambda row: (int(row["curriculum_order"]), str(row["id"])))
    return {"train": train, "validation": validation}


def _write_shards(
    root: Path,
    rows_by_split: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    disable_progress_bar()
    records: list[dict[str, Any]] = []
    for split in ("train", "validation"):
        rows = list(rows_by_split[split])
        plans = plan_shards(
            len(rows),
            max_rows_per_shard=MAX_ROWS_PER_SHARD,
            split=split,
        )
        for plan in plans:
            target = root / "data" / plan.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            dataset = Dataset.from_list(
                rows[plan.start : plan.stop],
                features=depth_features(),
            )
            dataset.to_parquet(str(target), batch_size=64)
            records.append(
                {
                    "split": split,
                    "index": plan.index,
                    "total": plan.total,
                    "path": target.relative_to(root).as_posix(),
                    "rows": plan.row_count,
                    "bytes": target.stat().st_size,
                    "sha256": depth_sha256_file(target),
                }
            )
    return records


def _write_factory_records(
    root: Path,
    anchors: Sequence[Mapping[str, Any]],
    contracts: Sequence[Mapping[str, Any]],
    plans: Sequence[Mapping[str, Any]],
    all_rows: Sequence[Mapping[str, Any]],
    core_snapshot: Mapping[str, str],
) -> None:
    write_json(
        root / "factory" / "anchor_manifest.json",
        {
            "core_digest_sha256": CORE_DIGEST,
            "core_grammar_catalog_sha256": CORE_GRAMMAR_CATALOG_SHA256,
            "representation_count": len(anchors),
            "anchors": [
                {
                    "code_sha256": anchor["code_sha256"],
                    "grammar_id": anchor["grammar_id"],
                    "id": anchor["id"],
                    "image_sha256": anchor["image_sha256"],
                    "level": anchor["level"],
                }
                for anchor in anchors
            ],
        },
    )
    write_json(
        root / "factory" / "variation_contracts.json",
        {
            "generator_version": GENERATOR_VERSION,
            "anchor_representation_count": len(anchors),
            "complete_depth_representation_count": DEPTH_ELIGIBLE_COUNT,
            "anchor_only_representation_count": len(ANCHOR_ONLY_PARENT_IDS),
            "anchor_only_parent_ids": sorted(ANCHOR_ONLY_PARENT_IDS),
            "representation_count": len(contracts),
            "contracts": list(contracts),
        },
    )
    write_json(
        root / "factory" / "generation_plan.json",
        {
            "generator_version": GENERATOR_VERSION,
            "anchor_representation_count": len(anchors),
            "complete_depth_representation_count": DEPTH_ELIGIBLE_COUNT,
            "anchor_only_representation_count": len(ANCHOR_ONLY_PARENT_IDS),
            "anchor_only_parent_ids": sorted(ANCHOR_ONLY_PARENT_IDS),
            "geometry_states_per_complete_representation": 8,
            "representation_count": len(plans),
            "schedule": {
                "r00": "approved core semantic anchor",
                "r01-r02": "two distinct primary-axis states",
                "r03-r04": "two distinct secondary-axis states or safe fallback",
                "r05-r06": "two distinct tertiary-axis states or safe fallback",
                "r07": "deterministic multi-axis interaction",
            },
            "plans": list(plans),
        },
    )
    write_json(
        root / "factory" / "accepted_manifest.json",
        {
            "accepted_only": True,
            "generator_version": GENERATOR_VERSION,
            "row_count": len(all_rows),
            "rows": [
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
                for row in sorted(all_rows, key=lambda item: str(item["id"]))
            ],
        },
    )
    write_json(
        root / "factory" / "core_reference_snapshot.json",
        {
            "core_digest_sha256": CORE_DIGEST,
            "reference_artifacts": dict(core_snapshot),
        },
    )


def _write_metadata(
    root: Path,
    all_rows: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
    contracts: Sequence[Mapping[str, Any]],
) -> None:
    level_counts = Counter(str(row["level"]) for row in all_rows)
    transform_counts = Counter(str(row["transform_kind"]) for row in all_rows)
    controlled_counts = Counter(
        axis for row in all_rows for axis in row["controlled_axes"]
    )
    write_json(
        root / "metadata" / "catalog.json",
        {
            "accepted_only": True,
            "anchor_only_parent_ids": sorted(ANCHOR_ONLY_PARENT_IDS),
            "anchor_only_representation_count": len(ANCHOR_ONLY_PARENT_IDS),
            "anchor_representation_count": APPROVED_REPRESENTATION_COUNT,
            "columns": list(DEPTH_ROW_COLUMNS),
            "complete_depth_representation_count": DEPTH_ELIGIBLE_COUNT,
            "core_rows_retained": CORE_ROW_COUNT,
            "generator_version": GENERATOR_VERSION,
            "level_counts": dict(sorted(level_counts.items())),
            "logical_release_sha256": manifest["logical_release_sha256"],
            "parent_core_digest_sha256": CORE_DIGEST,
            "representation_count": 547,
            "row_count": len(all_rows),
            "split_counts": manifest["split_counts"],
        },
    )
    write_json(
        root / "metadata" / "audit_report.json",
        {
            "accepted_only": True,
            "anchor_only_parent_ids": sorted(ANCHOR_ONLY_PARENT_IDS),
            "anchor_only_representation_count": len(ANCHOR_ONLY_PARENT_IDS),
            "anchor_representation_count": APPROVED_REPRESENTATION_COUNT,
            "complete_depth_representation_count": DEPTH_ELIGIBLE_COUNT,
            "controlled_axis_counts": dict(sorted(controlled_counts.items())),
            "core_reference_match": True,
            "geometry_states_per_complete_representation": 8,
            "logical_release_sha256": manifest["logical_release_sha256"],
            "representation_count": len(contracts),
            "row_count": len(all_rows),
            "transform_counts": dict(sorted(transform_counts.items())),
            "verification": {
                "all_controlled_programs_compiled_and_pure": True,
                "all_controlled_programs_executed": True,
                "all_controlled_source_grammars_preserved": True,
                "all_geometry_changes_have_input_signal": True,
                "all_ports_attached_and_signature_preserved": True,
                "all_representation_ids_come_from_core_v1": True,
            },
        },
    )


def _gallery_reference_paths(
    gallery_manifest: Mapping[str, Any],
) -> list[str]:
    """Return every generated gallery artifact under a safe relative path."""

    overview = gallery_manifest.get("overview")
    pages = gallery_manifest.get("pages")
    if not isinstance(overview, str) or not isinstance(pages, list):
        raise DepthBuildError("gallery manifest lacks overview or progression pages")
    if gallery_manifest.get("progression_page_count") != len(pages):
        raise DepthBuildError("gallery manifest progression count differs")
    paths = [overview]
    for record in pages:
        if not isinstance(record, Mapping) or not isinstance(record.get("path"), str):
            raise DepthBuildError("gallery manifest has a malformed page record")
        paths.append(str(record["path"]))
    if len(paths) != len(set(paths)):
        raise DepthBuildError("gallery manifest repeats an artifact path")
    for relative in paths:
        raw = Path(relative)
        if (
            raw.is_absolute()
            or ".." in raw.parts
            or raw.suffix.lower() != ".png"
            or not raw.is_relative_to("galleries")
        ):
            raise DepthBuildError(f"unsafe gallery artifact path: {relative!r}")
    return paths


def _promote(stage: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    backup = Path(
        tempfile.mkdtemp(prefix=".depth-v1-backup.", dir=output.parent)
    )
    moved_old: list[str] = []
    moved_new: list[str] = []
    try:
        for name in GENERATED_DIRECTORIES:
            source = stage / name
            if not source.is_dir():
                raise DepthBuildError(f"staged depth release lacks {name}/")
            destination = output / name
            if destination.exists():
                if not destination.is_dir():
                    raise DepthBuildError(f"generated path is not a directory: {name}")
                os.replace(destination, backup / name)
                moved_old.append(name)
            os.replace(source, destination)
            moved_new.append(name)
        write_checksums(output)
    except Exception:
        for name in reversed(moved_new):
            destination = output / name
            if destination.is_dir():
                shutil.rmtree(destination)
        for name in reversed(moved_old):
            os.replace(backup / name, output / name)
        raise
    finally:
        shutil.rmtree(backup, ignore_errors=True)


def _assert_frozen_logical_release(manifest: Mapping[str, Any]) -> None:
    observed = manifest.get("logical_release_sha256")
    if observed != FROZEN_LOGICAL_RELEASE_SHA256:
        raise DepthBuildError(
            "depth-v1 logical release digest differs from the frozen release: "
            f"{observed!r} != {FROZEN_LOGICAL_RELEASE_SHA256}"
        )


def _load_freeze(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DepthBuildError(f"{label} freeze is not readable JSON: {path}") from exc
    if not isinstance(value, dict):
        raise DepthBuildError(f"{label} freeze is not a JSON object: {path}")
    return value


def _frozen_reference_bindings(
    freeze: Mapping[str, Any],
) -> dict[str, str]:
    raw_references = freeze.get("reference_artifacts")
    manifest = freeze.get("manifest")
    if not isinstance(raw_references, dict) or not isinstance(manifest, dict):
        raise DepthBuildError("frozen release lacks exact artifact bindings")
    manifest_path = manifest.get("path")
    manifest_sha256 = manifest.get("sha256")
    bindings = {
        str(relative): str(digest)
        for relative, digest in raw_references.items()
    }
    if not isinstance(manifest_path, str) or not isinstance(
        manifest_sha256,
        str,
    ):
        raise DepthBuildError("frozen release manifest binding is malformed")
    if manifest_path in bindings and bindings[manifest_path] != manifest_sha256:
        raise DepthBuildError("frozen release binds its manifest inconsistently")
    bindings[manifest_path] = manifest_sha256
    for relative, digest in bindings.items():
        raw = Path(relative)
        if (
            not relative
            or raw.is_absolute()
            or ".." in raw.parts
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise DepthBuildError(
                f"frozen release artifact binding is malformed: {relative!r}"
            )
    return bindings


def _assert_frozen_replay(stage: Path, output: Path) -> None:
    """Refuse to replace a committed release with a non-identical replay."""

    committed_path = output / "factory" / "freeze.json"
    if not committed_path.exists():
        return
    staged_path = stage / "factory" / "freeze.json"
    if not staged_path.is_file():
        raise DepthBuildError("staged depth release lacks factory/freeze.json")

    committed = _load_freeze(committed_path, label="committed")
    staged = _load_freeze(staged_path, label="staged")
    drift: list[str] = []
    if staged != committed:
        drift.append("freeze object differs")

    for relative, expected in sorted(
        _frozen_reference_bindings(committed).items()
    ):
        candidate = stage / relative
        if not candidate.is_file():
            drift.append(f"missing staged artifact {relative}")
            continue
        observed = depth_sha256_file(candidate)
        if observed != expected:
            drift.append(f"changed staged artifact {relative}")
    if drift:
        raise DepthBuildError(
            "depth-v1 replay differs from the committed frozen release: "
            + ", ".join(drift)
        )


def build_depth_v1(dataset_root: Path, output: Path) -> dict[str, Any]:
    dataset_root = dataset_root.expanduser().resolve()
    output = output.expanduser().resolve()
    core_rows, freeze = _load_core(dataset_root)
    _assert_safe_output_path(dataset_root, output, freeze)
    before_snapshot = _core_snapshot(dataset_root, freeze)
    anchors, anchors_by_grammar = _semantic_anchors(core_rows)
    previous_directory = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="pixcell-depth-execution-") as raw:
        try:
            os.chdir(raw)
            descendants, contracts, plans = _build_descendants(anchors)
        finally:
            os.chdir(previous_directory)
    rows_by_split = _ordered_rows(core_rows, descendants, anchors_by_grammar)
    all_rows = [*rows_by_split["train"], *rows_by_split["validation"]]
    population = validate_depth_population(
        all_rows,
        expected_parent_core_digest_sha256=CORE_DIGEST,
    )
    if population["split_counts"] != EXPECTED_SPLIT_COUNTS:
        raise DepthBuildError("depth split population differs from frozen schedule")

    stage = Path(
        tempfile.mkdtemp(prefix=".depth-v1-stage.", dir=output.parent)
    )
    try:
        shard_records = _write_shards(stage, rows_by_split)
        _write_factory_records(
            stage,
            anchors,
            contracts,
            plans,
            all_rows,
            before_snapshot,
        )
        manifest = build_manifest(
            all_rows,
            shards=shard_records,
            depth_generator_version=GENERATOR_VERSION,
            expected_parent_core_digest_sha256=CORE_DIGEST,
        )
        _assert_frozen_logical_release(manifest)
        write_json(stage / "metadata" / "manifest.json", manifest)
        _write_metadata(stage, all_rows, manifest, contracts)
        gallery_manifest = render_galleries(stage)
        reference_paths = [
            record["path"] for record in shard_records
        ] + [
            "factory/accepted_manifest.json",
            "factory/anchor_manifest.json",
            "factory/core_reference_snapshot.json",
            "factory/generation_plan.json",
            "factory/variation_contracts.json",
            "metadata/audit_report.json",
            "metadata/catalog.json",
            "metadata/gallery_manifest.json",
            "metadata/manifest.json",
        ] + _gallery_reference_paths(gallery_manifest)
        depth_freeze = build_freeze(
            stage,
            manifest,
            manifest_path="metadata/manifest.json",
            reference_paths=reference_paths,
        )
        write_json(stage / "factory" / "freeze.json", depth_freeze)
        _assert_frozen_replay(stage, output)
        after_snapshot = _core_snapshot(dataset_root, freeze)
        if after_snapshot != before_snapshot:
            raise DepthBuildError("core-v1 changed while depth-v1 was being built")
        _promote(stage, output)
        return {
            **population,
            "gallery_progression_pages": gallery_manifest[
                "progression_page_count"
            ],
            "logical_release_sha256": manifest["logical_release_sha256"],
            "shard_count": len(shard_records),
        }
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=DATASET_ROOT,
        help="Parent PixCell dataset package containing frozen core-v1.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEPTH_ROOT,
        help="Isolated depth-v1 release root.",
    )
    args = parser.parse_args()
    report = build_depth_v1(args.dataset_root, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
