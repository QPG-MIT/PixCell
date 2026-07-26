#!/usr/bin/env python3
"""Audit frozen PixCell curriculum coverage from the public dataset package."""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
from PIL import Image

from _shared import LEVELS, ReleaseError, read_json, write_json


SCHEMA_VERSION = "pixcell-core-coverage-audit-v1"
ROW_COLUMNS = (
    "id",
    "level",
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
    "image",
    "code",
    "image_sha256",
    "normalized_d4_sha256",
    "code_sha256",
)
BRIDGES = (("L0", "L1"), ("L1", "L2"), ("L2", "L3"), ("L3", "L4"))
NEIGHBOR_MASK_SIZE = 64
NEIGHBOR_MASK_MARGIN = 2
NEIGHBOR_THRESHOLDS = (0.70, 0.80, 0.90, 0.95)
POPCOUNT = np.asarray([int(value).bit_count() for value in range(256)], dtype=np.uint8)
EXPANSION_ALLOCATION = {
    "L1": {
        "count": 12,
        "categories": {
            "missing_primitive_operation_closure": 8,
            "visible_terminal_port_operations": 4,
        },
    },
    "L2": {
        "count": 24,
        "categories": {
            "ported_body_terminal_motifs": 9,
            "approach_parallel_departure_coupling_motifs": 6,
            "split_rejoin_and_feedback_motifs": 4,
            "repeated_media_transition_motifs": 4,
            "graded_route_bank_motifs": 1,
        },
    },
    "L3": {
        "count": 32,
        "categories": {
            "multiport_body_flow_hierarchies": 4,
            "coupling_systems": 4,
            "interferometer_systems": 4,
            "resonator_graphs": 4,
            "repeated_media_systems": 4,
            "lattice_defect_systems": 4,
            "mode_evolution_systems": 4,
            "fpr_bank_systems": 4,
        },
    },
    "L4": {
        "count": 32,
        "categories": {
            "awg_fpr_components": 6,
            "resonant_and_distributed_filter_components": 6,
            "multiport_repeated_components": 4,
            "interferometer_loop_components": 4,
            "multimode_interface_components": 4,
            "split_recombine_components": 4,
            "grating_components": 2,
            "edge_interface_components": 2,
        },
    },
}
DEPRIORITIZED_AREAS = (
    {
        "area": "additional_generic_crossings",
        "reason": (
            "L4 already has ten crossing representations, all exact- and "
            "D4-distinct."
        ),
        "evidence": [
            "levels.L4.family_row_counts.Waveguide Crossings",
            "collisions",
        ],
    },
    {
        "area": "additional_plain_2x2_directional_couplers",
        "reason": (
            "Conventional, curved, adiabatic, and periodic coupling mechanisms "
            "already occupy substantial L4 capacity; the missing value is in "
            "curriculum bridges and higher-order systems."
        ),
        "evidence": [
            "levels.L4.family_row_counts",
            "l4_balance.template_counts.coupler",
        ],
    },
    {
        "area": "additional_single_ring_variants",
        "reason": (
            "Single-loop, structured-loop, and cavity families are populated; "
            "new work should change the resonant graph rather than ring dimensions."
        ),
        "evidence": ["levels.L4.family_row_counts"],
    },
    {
        "area": "parameter_only_tooth_pitch_or_count_variants",
        "reason": (
            "Pitch, count, or width changes without a new repetition law are "
            "realizations, not new representation grammars."
        ),
        "evidence": ["representation_realization_balance"],
    },
)


def _counter_dict(values: Counter[Any]) -> dict[str, int]:
    return {str(key): int(values[key]) for key in sorted(values, key=str)}


def _distribution(values: list[int]) -> dict[str, int]:
    return _counter_dict(Counter(values))


def _parquet_path(root: Path, level: str) -> Path:
    matches = sorted((root / "data" / level).glob("train-*.parquet"))
    if len(matches) != 1:
        raise ReleaseError(
            f"{level}: expected exactly one Parquet shard, found {len(matches)}"
        )
    return matches[0]


def _load_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for level in LEVELS:
        table = pq.read_table(_parquet_path(root, level), columns=list(ROW_COLUMNS))
        rows.extend(table.to_pylist())
    return sorted(rows, key=lambda row: (str(row["level"]), str(row["id"])))


def _grammar_rows(root: Path) -> dict[str, dict[str, Any]]:
    catalog = read_json(root / "factory" / "core-v1" / "grammar_catalog.json")
    rows = catalog.get("rows")
    if not isinstance(rows, list):
        raise ReleaseError("core grammar catalog has no rows")
    result = {str(row["id"]): row for row in rows}
    if len(result) != len(rows):
        raise ReleaseError("core grammar catalog contains duplicate ids")
    return result


def _parse_port_signature(row: dict[str, Any]) -> str:
    try:
        value = json.loads(str(row["port_signature_json"]))
    except json.JSONDecodeError as exc:
        raise ReleaseError(f"{row['id']}: malformed port signature") from exc
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        count = value.get("count")
        return f"count:{count}" if isinstance(count, int) else "object"
    return str(value)


def _concept_labels(rows: list[dict[str, Any]]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for row in rows:
        concept_id = str(row["concept_id"])
        label = str(row["id"])
        metadata_label = str(row.get("label", "")).split(":", 1)[0].strip()
        labels.setdefault(concept_id, metadata_label or label)
    return labels


def _level_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    representations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        representations[str(row["representation_id"])].append(row)

    family_representation_counts = Counter(
        str(group[0]["family"]) for group in representations.values()
    )
    role_counts = Counter(str(row["variation_role"]) for row in rows)
    augmented = sum(len(group) > 1 for group in representations.values())
    return {
        "row_count": len(rows),
        "representation_count": len(representations),
        "concept_count": len({str(row["concept_id"]) for row in rows}),
        "leakage_group_count": len(
            {str(row["leakage_group_id"]) for row in rows}
        ),
        "unique_image_count": len({str(row["image_sha256"]) for row in rows}),
        "unique_d4_count": len(
            {str(row["normalized_d4_sha256"]) for row in rows}
        ),
        "unique_code_count": len({str(row["code_sha256"]) for row in rows}),
        "role_row_counts": _counter_dict(role_counts),
        "rows_per_representation": _distribution(
            [len(group) for group in representations.values()]
        ),
        "anchor_only_representation_count": len(representations) - augmented,
        "augmented_representation_count": augmented,
        "family_row_counts": _counter_dict(
            Counter(str(row["family"]) for row in rows)
        ),
        "family_representation_counts": _counter_dict(
            family_representation_counts
        ),
    }


def _representation_balance(rows: list[dict[str, Any]]) -> dict[str, Any]:
    representations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        representations[str(row["representation_id"])].append(row)
    semantic_anchor_count = sum(
        sum(item["variation_role"] == "semantic" for item in group) == 1
        for group in representations.values()
    )
    high_level = [
        group
        for group in representations.values()
        if str(group[0]["level"]) in {"L3", "L4"}
    ]
    return {
        "representation_count": len(representations),
        "semantic_anchor_count": semantic_anchor_count,
        "all_representations_have_one_semantic_anchor": (
            semantic_anchor_count == len(representations)
        ),
        "role_row_counts": _counter_dict(
            Counter(str(row["variation_role"]) for row in rows)
        ),
        "anchor_only_representation_count": sum(
            len(group) == 1 for group in representations.values()
        ),
        "augmented_representation_count": sum(
            len(group) > 1 for group in representations.values()
        ),
        "representations_with_realization_rows": sum(
            any(item["variation_role"] == "realization" for item in group)
            for group in representations.values()
        ),
        "l3_l4_representation_count": len(high_level),
        "l3_l4_anchor_only_representation_count": sum(
            len(group) == 1 for group in high_level
        ),
        "interpretation": (
            "core-v1 prioritizes representation breadth. Controlled physical "
            "realizations should remain a separate future lane and must not be "
            "counted as new grammars."
        ),
    }


def _collision_detail(
    rows: list[dict[str, Any]],
    *,
    field: str,
) -> dict[str, Any]:
    row_by_id = {str(row["id"]): row for row in rows}
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(str(row["id"]))
    duplicate_groups = sorted(
        (sorted(group) for group in groups.values() if len(group) > 1),
        key=lambda group: tuple(group),
    )
    level_rows = Counter(
        str(row_by_id[example_id]["level"])
        for group in duplicate_groups
        for example_id in group
    )
    return {
        "group_count": len(duplicate_groups),
        "row_count": sum(len(group) for group in duplicate_groups),
        "group_size_distribution": _distribution(
            [len(group) for group in duplicate_groups]
        ),
        "row_level_counts": _counter_dict(level_rows),
        "all_groups_share_one_leakage_group": all(
            len(
                {
                    str(row_by_id[example_id]["leakage_group_id"])
                    for example_id in group
                }
            )
            == 1
            for group in duplicate_groups
        ),
        "groups": duplicate_groups,
    }


def _bridge_closure(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labels = _concept_labels(rows)
    result: dict[str, Any] = {}
    for lower, upper in BRIDGES:
        lower_concepts = sorted(
            {str(row["concept_id"]) for row in rows if row["level"] == lower}
        )
        references = Counter(
            str(prerequisite)
            for row in rows
            if row["level"] == upper
            for prerequisite in row["prerequisite_ids"]
        )
        missing = [concept for concept in lower_concepts if not references[concept]]
        result[f"{lower}_to_{upper}"] = {
            "lower_concept_count": len(lower_concepts),
            "referenced_concept_count": len(lower_concepts) - len(missing),
            "closure_fraction": (
                (len(lower_concepts) - len(missing)) / len(lower_concepts)
                if lower_concepts
                else 1.0
            ),
            "prerequisite_edge_count": sum(references.values()),
            "missing_concepts": missing,
            "missing_concept_labels": {
                concept: labels.get(concept, concept) for concept in missing
            },
            "reference_counts": {
                concept: int(references[concept]) for concept in lower_concepts
            },
        }
    return result


def _primitive_coverage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for level in (level.upper() for level in LEVELS):
        level_rows = [row for row in rows if row["level"] == level]
        representations: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in level_rows:
            representations[str(row["representation_id"])].append(row)
        row_counts = Counter(
            str(call) for row in level_rows for call in row["primitive_calls"]
        )
        representation_counts = Counter(
            str(call)
            for group in representations.values()
            for call in {
                str(value)
                for row in group
                for value in row["primitive_calls"]
            }
        )
        result[level] = {
            "row_counts": _counter_dict(row_counts),
            "representation_counts": _counter_dict(representation_counts),
        }
    return result


def _l1_operations(rows: list[dict[str, Any]]) -> dict[str, Any]:
    operations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["level"] == "L1":
            operations[str(row["concept_id"])].append(row)
    result: dict[str, Any] = {}
    for concept_id in sorted(operations):
        group = operations[concept_id]
        result[concept_id] = {
            "row_count": len(group),
            "representation_count": len(
                {str(row["representation_id"]) for row in group}
            ),
            "primitive_calls": sorted(
                {
                    str(call)
                    for row in group
                    for call in row["primitive_calls"]
                }
            ),
            "prerequisite_ids": sorted(
                {
                    str(prerequisite)
                    for row in group
                    for prerequisite in row["prerequisite_ids"]
                }
            ),
        }
    return result


def _semantic_anchors(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anchors = [row for row in rows if row["variation_role"] == "semantic"]
    representation_ids = [
        str(row["representation_id"]) for row in anchors
    ]
    if len(representation_ids) != len(set(representation_ids)):
        raise ReleaseError("semantic anchors do not map one-to-one to representations")
    return anchors


def _embedded_image_bytes(row: dict[str, Any]) -> bytes:
    value = row["image"]
    payload = value.get("bytes") if isinstance(value, dict) else None
    if not payload:
        raise ReleaseError(f"{row['id']}: missing embedded image")
    return bytes(payload)


def _normalized_neighbor_mask(row: dict[str, Any]) -> np.ndarray:
    payload = _embedded_image_bytes(row)
    try:
        with Image.open(io.BytesIO(payload)) as opened:
            array = np.asarray(opened.convert("L"))
    except OSError as exc:
        raise ReleaseError(f"{row['id']}: could not decode image") from exc
    mask = array < 245
    if not mask.any():
        raise ReleaseError(f"{row['id']}: image contains no material")
    ys, xs = np.nonzero(mask)
    crop = mask[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    available = NEIGHBOR_MASK_SIZE - 2 * NEIGHBOR_MASK_MARGIN
    scale = min(available / crop.shape[0], available / crop.shape[1])
    height = max(1, min(available, int(round(crop.shape[0] * scale))))
    width = max(1, min(available, int(round(crop.shape[1] * scale))))
    image = Image.fromarray(crop.astype(np.uint8) * 255, mode="L")
    fitted = np.asarray(
        image.resize((width, height), Image.Resampling.NEAREST)
    ) >= 128
    canvas = np.zeros((NEIGHBOR_MASK_SIZE, NEIGHBOR_MASK_SIZE), dtype=bool)
    x0 = (NEIGHBOR_MASK_SIZE - width) // 2
    y0 = (NEIGHBOR_MASK_SIZE - height) // 2
    canvas[y0 : y0 + height, x0 : x0 + width] = fitted
    return canvas


def _packed_d4(mask: np.ndarray) -> np.ndarray:
    variants = []
    for turns in range(4):
        rotated = np.rot90(mask, turns)
        variants.extend((rotated, np.fliplr(rotated)))
    return np.stack(
        [np.packbits(variant.reshape(-1)) for variant in variants]
    )


def _quantile_summary(values: np.ndarray) -> dict[str, float]:
    quantiles = np.quantile(values, [0.0, 0.5, 0.75, 0.9, 0.95, 0.99, 1.0])
    return {
        key: round(float(value), 8)
        for key, value in zip(
            ("minimum", "p50", "p75", "p90", "p95", "p99", "maximum"),
            quantiles,
            strict=True,
        )
    }


def _visual_neighbor_pressure(rows: list[dict[str, Any]]) -> dict[str, Any]:
    anchors = _semantic_anchors(rows)
    masks = [_normalized_neighbor_mask(row) for row in anchors]
    packed = np.stack([_packed_d4(mask) for mask in masks], axis=1)
    material_counts = np.asarray([int(mask.sum()) for mask in masks])
    nearest_scores = np.full(len(anchors), -1.0, dtype=float)
    nearest_indices = np.full(len(anchors), -1, dtype=int)
    threshold_counts = {f"{threshold:.2f}": 0 for threshold in NEIGHBOR_THRESHOLDS}
    threshold_family_counts = {
        f"{threshold:.2f}": {"same_family": 0, "different_family": 0}
        for threshold in NEIGHBOR_THRESHOLDS
    }
    pair_rows: list[tuple[float, str, str, int, int]] = []
    exact_d4_pair_exclusion_count = 0

    for left_index in range(len(anchors) - 1):
        right_indices = np.arange(left_index + 1, len(anchors))
        left = packed[0, left_index]
        intersections = POPCOUNT[
            np.bitwise_and(packed[:, left_index + 1 :, :], left)
        ].sum(axis=2)
        unions = (
            material_counts[left_index]
            + material_counts[left_index + 1 :][None, :]
            - intersections
        )
        similarities = (intersections / unions).max(axis=0)
        for offset, score_value in enumerate(similarities):
            right_index = int(right_indices[offset])
            left_row = anchors[left_index]
            right_row = anchors[right_index]
            if (
                left_row["normalized_d4_sha256"]
                == right_row["normalized_d4_sha256"]
            ):
                exact_d4_pair_exclusion_count += 1
                continue
            score = float(score_value)
            left_id = str(left_row["id"])
            right_id = str(right_row["id"])
            pair_rows.append((score, left_id, right_id, left_index, right_index))
            for index, neighbor in (
                (left_index, right_index),
                (right_index, left_index),
            ):
                current_neighbor = int(nearest_indices[index])
                if score > nearest_scores[index] or (
                    score == nearest_scores[index]
                    and (
                        current_neighbor < 0
                        or str(anchors[neighbor]["id"])
                        < str(anchors[current_neighbor]["id"])
                    )
                ):
                    nearest_scores[index] = score
                    nearest_indices[index] = neighbor
            same_family = left_row["family"] == right_row["family"]
            for threshold in NEIGHBOR_THRESHOLDS:
                if score < threshold:
                    continue
                key = f"{threshold:.2f}"
                threshold_counts[key] += 1
                family_key = "same_family" if same_family else "different_family"
                threshold_family_counts[key][family_key] += 1

    if np.any(nearest_indices < 0):
        raise ReleaseError("could not assign every semantic anchor a visual neighbor")
    pair_rows.sort(key=lambda item: (-item[0], item[1], item[2]))
    top_pairs = []
    for score, _, _, left_index, right_index in pair_rows[:50]:
        left = anchors[left_index]
        right = anchors[right_index]
        top_pairs.append(
            {
                "similarity": round(score, 8),
                "left_id": str(left["id"]),
                "right_id": str(right["id"]),
                "left_level": str(left["level"]),
                "right_level": str(right["level"]),
                "left_family": str(left["family"]),
                "right_family": str(right["family"]),
                "same_family": left["family"] == right["family"],
            }
        )
    nearest_same_family = sum(
        anchors[index]["family"] == anchors[int(nearest_indices[index])]["family"]
        for index in range(len(anchors))
    )
    return {
        "scope": "semantic_anchors_only",
        "anchor_count": len(anchors),
        "pair_count": len(pair_rows),
        "exact_d4_pair_exclusion_count": exact_d4_pair_exclusion_count,
        "normalization": {
            "size_px": [NEIGHBOR_MASK_SIZE, NEIGHBOR_MASK_SIZE],
            "margin_px": NEIGHBOR_MASK_MARGIN,
            "crop": "material_bbox",
            "fit": "uniform_aspect_preserving",
            "alignment": "maximum_over_d4",
            "metric": "binary_iou",
        },
        "admission_role": "review_only_not_an_automatic_duplicate_gate",
        "threshold_pair_counts": threshold_counts,
        "threshold_family_counts": threshold_family_counts,
        "nearest_similarity_quantiles": _quantile_summary(nearest_scores),
        "nearest_same_family_count": nearest_same_family,
        "nearest_different_family_count": len(anchors) - nearest_same_family,
        "top_non_exact_d4_pairs": top_pairs,
    }


class _CoarseProgramSkeleton(ast.NodeTransformer):
    """Remove literals and local names while retaining API/control structure."""

    def visit_Constant(self, node: ast.Constant) -> ast.Constant:
        if isinstance(node.value, str):
            node.value = ""
        elif isinstance(node.value, bool):
            node.value = False
        elif isinstance(node.value, (int, float, complex)):
            node.value = 0
        elif isinstance(node.value, bytes):
            node.value = b""
        return node

    def visit_Name(self, node: ast.Name) -> ast.Name:
        node.id = "_"
        return node

    def visit_arg(self, node: ast.arg) -> ast.arg:
        node.arg = "_"
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = "_"
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node.name = "_"
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.name = "_"
        return self.generic_visit(node)

    def visit_alias(self, node: ast.alias) -> ast.alias:
        node.asname = None
        return node

    def visit_Global(self, node: ast.Global) -> ast.Global:
        node.names = ["_"]
        return node

    def visit_Nonlocal(self, node: ast.Nonlocal) -> ast.Nonlocal:
        node.names = ["_"]
        return node


def _program_skeleton_hash(source: str) -> str:
    tree = _CoarseProgramSkeleton().visit(ast.parse(source))
    ast.fix_missing_locations(tree)
    payload = ast.dump(tree, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _program_template_pressure(rows: list[dict[str, Any]]) -> dict[str, Any]:
    anchors = _semantic_anchors(rows)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in anchors:
        groups[_program_skeleton_hash(str(row["code"]))].append(row)
    reused = [
        (digest, sorted(group, key=lambda row: str(row["id"])))
        for digest, group in groups.items()
        if len(group) > 1
    ]
    reused.sort(key=lambda item: (-len(item[1]), item[0]))
    same_family_pairs = 0
    different_family_pairs = 0
    same_level_pairs = 0
    different_level_pairs = 0
    rendered_groups = []
    for digest, group in reused:
        total_pairs = len(group) * (len(group) - 1) // 2
        family_counts = Counter(str(row["family"]) for row in group)
        level_counts = Counter(str(row["level"]) for row in group)
        group_same_family = sum(
            count * (count - 1) // 2 for count in family_counts.values()
        )
        group_same_level = sum(
            count * (count - 1) // 2 for count in level_counts.values()
        )
        same_family_pairs += group_same_family
        different_family_pairs += total_pairs - group_same_family
        same_level_pairs += group_same_level
        different_level_pairs += total_pairs - group_same_level
        rendered_groups.append(
            {
                "skeleton_sha256": digest,
                "row_count": len(group),
                "level_counts": _counter_dict(level_counts),
                "family_counts": _counter_dict(family_counts),
                "ids": [str(row["id"]) for row in group],
            }
        )
    return {
        "scope": "semantic_anchors_only",
        "anchor_count": len(anchors),
        "skeleton_schema": "coarse_ast_literals_and_local_names_removed_v1",
        "admission_role": "review_only_not_an_automatic_duplicate_gate",
        "unique_skeleton_count": len(groups),
        "reused_skeleton_group_count": len(reused),
        "rows_in_reused_skeleton_groups": sum(
            len(group) for _, group in reused
        ),
        "maximum_group_size": max((len(group) for group in groups.values()), default=0),
        "group_size_distribution": _distribution(
            [len(group) for group in groups.values()]
        ),
        "reuse_pair_counts": {
            "same_family": same_family_pairs,
            "different_family": different_family_pairs,
            "same_level": same_level_pairs,
            "different_level": different_level_pairs,
        },
        "reused_groups": rendered_groups,
    }


def _port_balance(
    rows: list[dict[str, Any]],
    *,
    level: str,
) -> dict[str, Any]:
    level_rows = [row for row in rows if row["level"] == level]
    signature_counts = Counter(_parse_port_signature(row) for row in level_rows)
    family_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for row in level_rows:
        family_counts[str(row["family"])][_parse_port_signature(row)] += 1
    dominant = max(signature_counts.values(), default=0)
    return {
        "row_count": len(level_rows),
        "signature_counts": _counter_dict(signature_counts),
        "dominant_signature_share": (
            dominant / len(level_rows) if level_rows else 0.0
        ),
        "family_signature_counts": {
            family: _counter_dict(counts)
            for family, counts in sorted(family_counts.items())
        },
    }


def _l4_balance(
    rows: list[dict[str, Any]],
    grammar_rows: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    l4_rows = [row for row in rows if row["level"] == "L4"]
    templates: Counter[str] = Counter()
    mechanisms: Counter[str] = Counter()
    family_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in l4_rows:
        grammar = grammar_rows[str(row["id"])]
        factors = grammar.get("factor_assignment", {}).get(
            "representation_factors"
        )
        if not isinstance(factors, dict):
            raise ReleaseError(f"{row['id']}: missing L4 representation factors")
        templates[str(factors["template_id"])] += 1
        mechanisms[str(factors["mechanism"])] += 1
        family_rows[str(row["family"])].append(
            {
                "port_signature": _parse_port_signature(row),
                "mechanism": str(factors["mechanism"]),
            }
        )

    family_balance: dict[str, Any] = {}
    for family, group in sorted(family_rows.items()):
        family_balance[family] = {
            "row_count": len(group),
            "unique_mechanism_count": len(
                {str(item["mechanism"]) for item in group}
            ),
            "port_signature_counts": _counter_dict(
                Counter(str(item["port_signature"]) for item in group)
            ),
        }
    simple_ports = sum(
        1
        for row in l4_rows
        if _parse_port_signature(row) in {"1x1", "2x2"}
    )
    return {
        "row_count": len(l4_rows),
        "unique_mechanism_count": len(mechanisms),
        "template_counts": _counter_dict(templates),
        "mechanism_counts": _counter_dict(mechanisms),
        "repeated_mechanism_counts": {
            mechanism: count
            for mechanism, count in _counter_dict(mechanisms).items()
            if count > 1
        },
        "one_by_one_or_two_by_two_count": simple_ports,
        "one_by_one_or_two_by_two_share": simple_ports / len(l4_rows),
        "family_balance": family_balance,
    }


def _expansion_plan() -> dict[str, Any]:
    total = sum(int(level["count"]) for level in EXPANSION_ALLOCATION.values())
    category_total = sum(
        sum(int(count) for count in level["categories"].values())
        for level in EXPANSION_ALLOCATION.values()
    )
    if total != 100 or category_total != total:
        raise ReleaseError("expansion allocation must total exactly 100 grammars")
    return {
        "status": "approval_proposal_only",
        "new_representation_grammar_count": total,
        "counts_as_realization_or_pose": False,
        "levels": EXPANSION_ALLOCATION,
        "evidence_basis": {
            "L1": [
                "prerequisite_bridges.L0_to_L1.missing_concepts",
                "port_balance.L2",
            ],
            "L2": [
                "port_balance.L2",
                "prerequisite_bridges.L2_to_L3.missing_concepts",
            ],
            "L3": [
                "prerequisite_bridges.L3_to_L4",
                "l4_balance",
            ],
            "L4": [
                "l4_balance.family_balance",
                "port_balance.L4",
                "l4_balance.template_counts",
            ],
        },
        "deprioritized_areas": list(DEPRIORITIZED_AREAS),
        "later_separate_lanes": [
            "controlled_realizations",
            "useful_pose_examples",
            "render_companions",
            "failure_derived_repair_trajectories",
        ],
    }


def build_audit(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    freeze = read_json(root / "factory" / "core-v1" / "freeze.json")
    catalog = read_json(root / "metadata" / "catalog.json")
    rows = _load_rows(root)
    grammar_rows = _grammar_rows(root)

    frozen_rows = int(freeze["row_count"])
    frozen_representations = int(freeze["representation_count"])
    release_digest = str(freeze["release_digest_sha256"])
    if len(rows) != frozen_rows:
        raise ReleaseError(
            f"row count drift: public={len(rows)} frozen={frozen_rows}"
        )
    representation_count = len(
        {str(row["representation_id"]) for row in rows}
    )
    if representation_count != frozen_representations:
        raise ReleaseError(
            "representation count drift: "
            f"public={representation_count} frozen={frozen_representations}"
        )
    if catalog.get("release_digest_sha256") != release_digest:
        raise ReleaseError("metadata/freeze release digest mismatch")
    if len(grammar_rows) != frozen_rows:
        raise ReleaseError("grammar catalog row count drift")
    if set(grammar_rows) != {str(row["id"]) for row in rows}:
        raise ReleaseError("grammar/public row ids differ")

    by_level = {
        level.upper(): [row for row in rows if row["level"] == level.upper()]
        for level in LEVELS
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "core": {
            "name": str(freeze["core_name"]),
            "release_digest_sha256": release_digest,
            "row_count": frozen_rows,
            "representation_count": frozen_representations,
            "accepted_only": bool(freeze["accepted_only"]),
        },
        "levels": {
            level: _level_summary(level_rows)
            for level, level_rows in by_level.items()
        },
        "representation_realization_balance": _representation_balance(rows),
        "collisions": {
            "unique_image_count": len(
                {str(row["image_sha256"]) for row in rows}
            ),
            "unique_d4_count": len(
                {str(row["normalized_d4_sha256"]) for row in rows}
            ),
            "exact": _collision_detail(rows, field="image_sha256"),
            "d4": _collision_detail(rows, field="normalized_d4_sha256"),
            "interpretation": (
                "Reported aliases and pose/calibration examples are retained. "
                "Every exact and D4 group is contained by leakage_group_id."
            ),
        },
        "non_exact_review_pressure": {
            "visual_neighbors": _visual_neighbor_pressure(rows),
            "program_skeletons": _program_template_pressure(rows),
            "interpretation": (
                "These deterministic signals prioritize curator review. "
                "Neither silhouette similarity nor coarse AST reuse proves "
                "semantic duplication."
            ),
        },
        "prerequisite_bridges": _bridge_closure(rows),
        "primitive_coverage": _primitive_coverage(rows),
        "l1_operation_coverage": _l1_operations(rows),
        "port_balance": {
            "L2": _port_balance(rows, level="L2"),
            "L4": _port_balance(rows, level="L4"),
        },
        "l4_balance": _l4_balance(rows, grammar_rows),
        "expansion_plan": _expansion_plan(),
        "evidence_paths": [
            "factory/core-v1/freeze.json",
            "factory/core-v1/grammar_catalog.json",
            "metadata/catalog.json",
            "metadata/audit_report.json",
            "metadata/source_reports/l0.json",
            "metadata/source_reports/l1.json",
            "metadata/source_reports/l2.json",
            "metadata/source_reports/l3.json",
            "metadata/source_reports/l4.json",
            "data/l0/train-00000-of-00001.parquet",
            "data/l1/train-00000-of-00001.parquet",
            "data/l2/train-00000-of-00001.parquet",
            "data/l3/train-00000-of-00001.parquet",
            "data/l4/train-00000-of-00001.parquet",
        ],
    }

    expected_collisions = catalog.get("collision_report", {})
    if (
        report["collisions"]["exact"]["group_count"]
        != expected_collisions.get("exact_duplicate_group_count")
        or report["collisions"]["d4"]["group_count"]
        != expected_collisions.get("d4_equivalent_group_count")
        or report["collisions"]["exact"]["groups"]
        != expected_collisions.get("exact_duplicate_groups")
        or report["collisions"]["d4"]["groups"]
        != expected_collisions.get("d4_equivalent_groups")
    ):
        raise ReleaseError("derived collisions differ from metadata catalog")
    return report


def _percentage(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend(
        "| " + " | ".join(str(value) for value in row) + " |" for row in rows
    )
    return lines


def render_markdown(report: dict[str, Any]) -> str:
    core = report["core"]
    levels = report["levels"]
    collisions = report["collisions"]
    pressure = report["non_exact_review_pressure"]
    bridges = report["prerequisite_bridges"]
    l4 = report["l4_balance"]
    expansion = report["expansion_plan"]
    lines = [
        "# PixCell `core-v1` coverage audit",
        "",
        (
            f"Frozen release `{core['release_digest_sha256']}` contains "
            f"{core['row_count']} accepted rows and "
            f"{core['representation_count']} representation grammars."
        ),
        "",
        "## Core balance",
        "",
    ]
    lines.extend(
        _markdown_table(
            [
                "Level",
                "Rows",
                "Representations",
                "Concepts",
                "Unique images",
                "Unique D4",
                "Anchor-only",
            ],
            [
                [
                    level,
                    values["row_count"],
                    values["representation_count"],
                    values["concept_count"],
                    values["unique_image_count"],
                    values["unique_d4_count"],
                    values["anchor_only_representation_count"],
                ]
                for level, values in levels.items()
            ],
        )
    )
    balance = report["representation_realization_balance"]
    lines.extend(
        [
            "",
            "Role balance:",
            "",
            *[
                f"- `{role}`: {count}"
                for role, count in balance["role_row_counts"].items()
            ],
            (
                f"- {balance['anchor_only_representation_count']}/"
                f"{balance['representation_count']} representations are "
                "anchor-only."
            ),
            (
                f"- All {balance['l3_l4_representation_count']} L3/L4 "
                "representations are anchor-only."
            ),
            "",
            "## Duplicate and D4 telemetry",
            "",
            (
                f"- {collisions['unique_image_count']} unique images and "
                f"{collisions['unique_d4_count']} unique D4 silhouettes."
            ),
            (
                f"- {collisions['exact']['group_count']} exact groups involving "
                f"{collisions['exact']['row_count']} rows."
            ),
            (
                f"- {collisions['d4']['group_count']} D4-equivalent groups "
                f"involving {collisions['d4']['row_count']} rows."
            ),
            (
                "- Every reported exact/D4 group remains inside one "
                "`leakage_group_id`."
            ),
            "",
            "## Non-exact review pressure",
            "",
            (
                "The following telemetry is deterministic curator triage, not "
                "an automatic duplicate or admission gate."
            ),
            "",
        ]
    )
    visual_pressure = pressure["visual_neighbors"]
    skeleton_pressure = pressure["program_skeletons"]
    lines.extend(
        _markdown_table(
            ["Aligned silhouette IoU", "Anchor pairs", "Same family", "Different"],
            [
                [
                    f"≥ {threshold}",
                    count,
                    visual_pressure["threshold_family_counts"][threshold][
                        "same_family"
                    ],
                    visual_pressure["threshold_family_counts"][threshold][
                        "different_family"
                    ],
                ]
                for threshold, count in visual_pressure[
                    "threshold_pair_counts"
                ].items()
            ],
        )
    )
    nearest_quantiles = visual_pressure["nearest_similarity_quantiles"]
    lines.extend(
        [
            "",
            (
                "Nearest-neighbor aligned-IoU quantiles across semantic anchors: "
                f"p50 {nearest_quantiles['p50']:.3f}, "
                f"p90 {nearest_quantiles['p90']:.3f}, "
                f"p99 {nearest_quantiles['p99']:.3f}, "
                f"max {nearest_quantiles['maximum']:.3f}."
            ),
            (
                f"The coarse AST skeleton pass finds "
                f"{skeleton_pressure['unique_skeleton_count']} templates across "
                f"{skeleton_pressure['anchor_count']} anchors; "
                f"{skeleton_pressure['rows_in_reused_skeleton_groups']} rows "
                f"belong to {skeleton_pressure['reused_skeleton_group_count']} "
                "reused groups."
            ),
            "",
            "Highest non-exact/D4 silhouette-pressure pairs:",
            "",
        ]
    )
    lines.extend(
        _markdown_table(
            ["Left", "Right", "IoU", "Same family"],
            [
                [
                    f"`{pair['left_id']}`",
                    f"`{pair['right_id']}`",
                    f"{pair['similarity']:.3f}",
                    pair["same_family"],
                ]
                for pair in visual_pressure["top_non_exact_d4_pairs"][:10]
            ],
        )
    )
    lines.extend(
        [
            "",
            "## Prerequisite closure",
            "",
        ]
    )
    lines.extend(
        _markdown_table(
            ["Bridge", "Reached", "Edges", "Missing concepts"],
            [
                [
                    key.replace("_to_", " → "),
                    (
                        f"{value['referenced_concept_count']}/"
                        f"{value['lower_concept_count']}"
                    ),
                    value["prerequisite_edge_count"],
                    ", ".join(f"`{item}`" for item in value["missing_concepts"])
                    or "None",
                ]
                for key, value in bridges.items()
            ],
        )
    )
    l2_ports = report["port_balance"]["L2"]
    l4_ports = report["port_balance"]["L4"]
    lines.extend(
        [
            "",
            (
                "The largest discontinuity is L3 → L4: no L4 row declares an "
                "L3 prerequisite. L2 also leaves the direct coupling precursor "
                "`l2_15_approach_parallel_departure_pair` unused at L3."
            ),
            "",
            "## Port balance",
            "",
        ]
    )
    lines.extend(
        _markdown_table(
            ["Level", "Port signature", "Rows"],
            [
                [level, signature, count]
                for level, values in (("L2", l2_ports), ("L4", l4_ports))
                for signature, count in values["signature_counts"].items()
            ],
        )
    )
    lines.extend(
        [
            "",
            (
                f"L2 assigns `0x0` to "
                f"{l2_ports['signature_counts'].get('0x0', 0)}/"
                f"{l2_ports['row_count']} rows. L4 assigns `1x1` or `2x2` to "
                f"{l4['one_by_one_or_two_by_two_count']}/{l4['row_count']} "
                f"rows ({_percentage(l4['one_by_one_or_two_by_two_share'])})."
            ),
            "",
            "## L4 mechanism balance",
            "",
            (
                f"L4 contains {l4['unique_mechanism_count']} distinct declared "
                f"mechanisms across {l4['row_count']} rows."
            ),
            "",
        ]
    )
    lines.extend(
        _markdown_table(
            ["Template", "Rows"],
            [
                [template, count]
                for template, count in l4["template_counts"].items()
            ],
        )
    )
    lines.extend(["", "Family balance:", ""])
    lines.extend(
        _markdown_table(
            ["Family", "Rows", "Unique mechanisms", "Ports"],
            [
                [
                    family,
                    values["row_count"],
                    values["unique_mechanism_count"],
                    ", ".join(
                        f"{port}: {count}"
                        for port, count in values["port_signature_counts"].items()
                    ),
                ]
                for family, values in l4["family_balance"].items()
            ],
        )
    )
    lines.extend(
        [
            "",
            "## Proposed approval wave",
            "",
            (
                "This is an evidence-backed proposal for 100 new representation "
                "grammars. It does not allocate realizations, poses, renders, or "
                "repair trajectories."
            ),
            "",
        ]
    )
    lines.extend(
        _markdown_table(
            ["Level", "New grammars", "Allocation"],
            [
                [
                    level,
                    values["count"],
                    "; ".join(
                        f"`{category}` {count}"
                        for category, count in values["categories"].items()
                    ),
                ]
                for level, values in expansion["levels"].items()
            ],
        )
    )
    lines.extend(["", "Deprioritized:", ""])
    lines.extend(
        f"- `{item['area']}` — {item['reason']}"
        for item in expansion["deprioritized_areas"]
    )
    lines.extend(
        [
            "",
            "## Evidence",
            "",
            *[f"- `{path}`" for path in report["evidence_paths"]],
            "",
            (
                "Generated deterministically by "
                "`python scripts/audit_coverage.py --root .`."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_audit(
    root: Path,
    *,
    json_output: Path,
    markdown_output: Path,
) -> dict[str, Any]:
    report = build_audit(root)
    write_json(json_output, report)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(render_markdown(report), encoding="utf-8")
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Dataset package root (default: parent of scripts/).",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="JSON output path (default: factory/expansion/core-v1-coverage.json).",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Markdown output path (default: factory/expansion/core-v1-coverage.md).",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    root = args.root.expanduser().resolve()
    json_output = args.json_output or (
        root / "factory" / "expansion" / "core-v1-coverage.json"
    )
    markdown_output = args.markdown_output or (
        root / "factory" / "expansion" / "core-v1-coverage.md"
    )
    report = write_audit(
        root,
        json_output=json_output.expanduser().resolve(),
        markdown_output=markdown_output.expanduser().resolve(),
    )
    print(
        json.dumps(
            {
                "core_name": report["core"]["name"],
                "release_digest_sha256": report["core"][
                    "release_digest_sha256"
                ],
                "row_count": report["core"]["row_count"],
                "representation_count": report["core"][
                    "representation_count"
                ],
                "new_representation_grammar_proposals": report[
                    "expansion_plan"
                ]["new_representation_grammar_count"],
                "json_output": json_output.relative_to(root).as_posix(),
                "markdown_output": markdown_output.relative_to(root).as_posix(),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
