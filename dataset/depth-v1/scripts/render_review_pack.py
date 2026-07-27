#!/usr/bin/env python3
"""Render a compact, parameter-labeled review pack from depth-v1 Parquet.

This is deliberately separate from the release galleries.  It selects a
curated cross-section of complete r00-r07 realization groups, displays the
exact model image from each Parquet row, and derives every displayed parameter
label from ``parameter_delta_json``.  It is a review-only artifact, not part of
the frozen release, and never executes or re-renders a target program.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shutil
import tempfile
import textwrap
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import pyarrow.parquet as pq
from PIL import Image, ImageDraw, ImageFont, ImageOps

import schema as depth_schema


STATE_SLOTS = tuple(range(8))
LEFT_WIDTH = 310
CELL_WIDTH = 190
ROW_HEIGHT = 242
HEADER_HEIGHT = 94
IMAGE_SIZE = 136
PNG_COMPRESSION = 9


@dataclass(frozen=True)
class Pick:
    """One intentionally selected representation and why it is useful."""

    grammar_id: str
    rationale: str


@dataclass(frozen=True)
class SheetSpec:
    """One approval sheet and its curated representation cross-section."""

    slug: str
    title: str
    summary: str
    picks: tuple[Pick, ...]


SHEETS = (
    SheetSpec(
        slug="01-primitives",
        title="L0 · primitive geometry",
        summary=(
            "Basic filled shapes, routed curves, paired rails, paths, tapers, "
            "and a spiral."
        ),
        picks=(
            Pick("g_893acd0ec3151d5eae07", "equal-axis rectangle"),
            Pick("g_35cad8c233ec1f971f8b", "annulus with visible wall"),
            Pick("g_a2b970c7d908676a5762", "orthogonal cross body"),
            Pick("g_028fd1f12a2521a8d04f", "right-triangle silhouette"),
            Pick("g_aae899a2a998f4339b96", "anisotropic ellipse"),
            Pick("g_1b60cd40859bcb3d5b9a", "six-sided regular polygon"),
            Pick("g_cf57549f011e9ba43a2a", "unequal-leg concave L"),
            Pick("g_2a7e8fa58fcd9e2dfc34", "Euler quarter bend"),
            Pick("g_fce2058b6f5bc83c5756", "offset S-bend"),
            Pick("g_72075acbffecff838008", "inflected Bezier route"),
            Pick("g_ef74120b3121c58a2008", "linear width transition"),
            Pick("g_69ffd5d44dbe9c317101", "two-rail straight coupler"),
            Pick("g_92e853d55b966b89bbd6", "smoothed waypoint route"),
            Pick("g_d1aaa3f41bddda724f28", "two-loop spiral path"),
        ),
    ),
    SheetSpec(
        slug="02-operations-compositions",
        title="L1–L2 · operations and compositions",
        summary=(
            "Rigid transforms, spatial relations, Boolean construction, "
            "routing, repetition, branching, and composite arrays."
        ),
        picks=(
            Pick("l1_02_rotate__c1", "rigid rotation of a heterogeneous group"),
            Pick("l1_03_mirror__b2", "three-body chiral reflection"),
            Pick("l1_04_center_align__c1", "three-body nested alignment"),
            Pick("l1_06_gap__b1", "measured ring-to-bus gap"),
            Pick("l1_07_tangency__c2", "two-sided contact relation"),
            Pick("l1_09_connect__c2", "compound connected path"),
            Pick("l1_15_boolean_not__c1", "multi-hole Boolean subtraction"),
            Pick("l1_16_boolean_xor__c2", "concave exclusive regions"),
            Pick("l1_18_radial_repetition__b2", "oriented partial radial fan"),
            Pick("l1_19_array_2d__c1", "two-dimensional cross array"),
            Pick("l1_20_route_single__c2", "multi-turn terminal routing"),
            Pick("l2_01_mirrored_fixed_gap_pair__s01", "mirrored taper pair"),
            Pick("l2_14_local_branch_junction__s04", "asymmetric local fork"),
            Pick(
                "l2_15_approach_parallel_departure_pair__s05",
                "flared interaction window",
            ),
            Pick(
                "l2_16_repeated_carrier_combination__s04",
                "chirped repeated carrier",
            ),
            Pick("l2_17_composite_cell_2d_array__s04", "composite cell lattice"),
            Pick("l2_20_oriented_radial_bank__s03", "spiraling petal bank"),
        ),
    ),
    SheetSpec(
        slug="03-networks-repeated-media",
        title="L3 · networks and repeated media",
        summary=(
            "Hierarchical paths, branches, body-route systems, defects, "
            "supercells, radial hubs, and cyclic graphs."
        ),
        picks=(
            Pick(
                "l3_01_serial_heterogeneous_chain_s03",
                "serial signed-curve width chain",
            ),
            Pick(
                "l3_02_parallel_reconvergent_bundle_s05",
                "nested reconvergent branch",
            ),
            Pick(
                "l3_03_recursive_asymmetric_branch_hierarchy_s05",
                "unequal recursive tree",
            ),
            Pick(
                "l3_04_persistent_trunk_with_side_branches_s03",
                "multi-axis tapped trunk",
            ),
            Pick(
                "l3_07_constructive_body_terminal_system_s06",
                "annular body with radial terminals",
            ),
            Pick(
                "l3_10_obstacle_constrained_route_bundle_s03",
                "multi-route obstacle avoidance",
            ),
            Pick(
                "l3_11_transition_repeated_transition_spine_s03",
                "graded repeated spine",
            ),
            Pick(
                "l3_13_dual_bank_local_defect_s06",
                "phase-slip defect between banks",
            ),
            Pick(
                "l3_14_supercell_array_with_channel_or_defect_s03",
                "diagonal channel in a supercell array",
            ),
            Pick(
                "l3_15_constructive_hub_radial_hierarchy_s04",
                "two-rank radial fork hierarchy",
            ),
            Pick(
                "l3_16_multi_axis_hub_terminal_routes_s06",
                "multi-axis heterogeneous routes",
            ),
            Pick(
                "l3_19_multi_body_routed_assembly_s03",
                "routed cycle with terminals",
            ),
            Pick(
                "l3_21_branch_coupled_repeated_media_s05",
                "branch-local vacancy and substitution",
            ),
            Pick(
                "l3_22_cyclic_carrier_terminal_graph_s06",
                "concentric cyclic terminal graph",
            ),
        ),
    ),
    SheetSpec(
        slug="04-photonic-devices",
        title="L4 · photonic devices",
        summary=(
            "Splitters, MMIs, directional and adiabatic couplers, resonators, "
            "interferometers, and crossings."
        ),
        picks=(
            Pick("mmi_block_1x2", "full-access 1x2 MMI"),
            Pick("mmi_splitter_1x4", "resolved four-channel MMI"),
            Pick("y_branch_smooth_1x2", "smooth Y branch"),
            Pick("splitter_tree_1x4", "explicit two-stage splitter tree"),
            Pick("directional_side_tap_coupler_1x2", "generic 1x2 side tap"),
            Pick(
                "directional_coupler_sbend_2x2",
                "conventional 2x2 directional coupler",
            ),
            Pick(
                "directional_coupler_dual_window_2x2",
                "dual interaction-window coupler",
            ),
            Pick(
                "adiabatic_mode_evolution_coupler_1x2",
                "complementary adiabatic exchange",
            ),
            Pick("adiabatic_coupler_full_2x2", "full-access adiabatic 2x2"),
            Pick("ring_bus_drop", "four-port ring drop"),
            Pick(
                "bragg_loaded_racetrack_resonator_1x1",
                "structured racetrack resonator",
            ),
            Pick("mzi_hexagonal", "angular MZI topology"),
            Pick("mzi_unbalanced", "unequal-arm MZI"),
            Pick("crossing_curved_x", "continuous-curvature crossing"),
            Pick("adiabatic_crossing_2x2", "four-lobe adiabatic crossing"),
        ),
    ),
    SheetSpec(
        slug="05-structured-photonics",
        title="L4 · structured photonics",
        summary=(
            "Chirped and segmented gratings, periodic couplers, defect "
            "cavities, edge/mode converters, and free-propagation fans."
        ),
        picks=(
            Pick(
                "chirped_apodized_tapered_grating_1x0",
                "chirped and apodized tapered teeth",
            ),
            Pick(
                "segmented_swg_grating_coupler_1x0",
                "segmented subwavelength tapered grating",
            ),
            Pick("focusing_grating_coupler_arcs", "curved focusing teeth"),
            Pick(
                "apodized_hole_lattice_grating_1x0",
                "graded two-dimensional hole lattice",
            ),
            Pick(
                "corrugated_contra_directional_coupler_2x2",
                "corrugated interaction region",
            ),
            Pick("swg_directional_coupler_2x2", "segmented 2x2 coupler"),
            Pick(
                "nanobeam_hole_defect_cavity_1x1",
                "hole-defect nanobeam cavity",
            ),
            Pick(
                "phase_shifted_bragg_cavity_1x1",
                "phase-shifted Bragg cavity",
            ),
            Pick(
                "photonic_crystal_line_defect_cavity_1x1",
                "two-dimensional line defect",
            ),
            Pick("apodized_swg_edge_coupler_1x1", "apodized edge converter"),
            Pick(
                "segmented_trident_edge_coupler_3x1",
                "segmented multi-tip edge converter",
            ),
            Pick("slot_to_strip_converter_1x1", "slot-to-strip evolution"),
            Pick(
                "polarization_splitter_rotator_1x2",
                "polarization splitter-rotator",
            ),
            Pick("star_coupler_2x4", "two-by-four star coupler"),
            Pick("star_fan_1x4", "one-by-four free-propagation fan"),
            Pick("double_sidewall_tooth_array", "apodized bilateral teeth"),
        ),
    ),
)


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    names = (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "Arial Bold.ttf" if bold else "Arial.ttf",
    )
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _json_object(value: Any, *, field: str, row_id: str) -> dict[str, Any]:
    try:
        parsed = json.loads(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{row_id}: invalid {field}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{row_id}: {field} is not an object")
    return parsed


def _load_rows(root: Path) -> tuple[list[dict[str, Any]], list[Path]]:
    paths = [
        path
        for split in ("train", "validation")
        for path in sorted((root / "data").glob(f"{split}-*.parquet"))
    ]
    if not paths:
        raise ValueError(f"no Parquet shards found below {root / 'data'}")
    rows: list[dict[str, Any]] = []
    for path in paths:
        rows.extend(pq.read_table(path).to_pylist())
    return rows, paths


def _group_sweeps(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, dict[int, Mapping[str, Any]]], tuple[str, ...]]:
    grouped: dict[str, dict[int, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        slot = int(row["realization_slot"])
        if slot not in STATE_SLOTS:
            continue
        grammar_id = str(row["grammar_id"])
        if slot in grouped[grammar_id]:
            raise ValueError(f"duplicate state: {grammar_id}/r{slot:02d}")
        grouped[grammar_id][slot] = row

    complete: dict[str, dict[int, Mapping[str, Any]]] = {}
    anchor_only: list[str] = []
    for grammar_id, states in sorted(grouped.items()):
        slots = set(states)
        if slots == set(STATE_SLOTS):
            complete[grammar_id] = states
        elif slots == {0}:
            anchor_only.append(grammar_id)
        else:
            raise ValueError(
                f"{grammar_id}: expected r00 only or r00-r07, got "
                f"{sorted(slots)}"
            )

    declared = {
        str(value)
        for value in getattr(depth_schema, "ANCHOR_ONLY_PARENT_IDS", ())
    }
    declared.update(
        str(value)
        for value in getattr(depth_schema, "ANCHOR_ONLY_GRAMMAR_IDS", ())
    )
    if declared:
        keys_by_grammar = {
            grammar_id: {
                grammar_id,
                str(grouped[grammar_id][0]["id"]),
                str(grouped[grammar_id][0]["parent_core_id"]),
            }
            for grammar_id in anchor_only
        }
        unmatched_observed = [
            grammar_id
            for grammar_id, keys in keys_by_grammar.items()
            if keys.isdisjoint(declared)
        ]
        matched_declared = {
            value
            for keys in keys_by_grammar.values()
            for value in keys & declared
        }
        unmatched_declared = sorted(declared - matched_declared)
        if unmatched_observed or unmatched_declared:
            raise ValueError(
                "anchor-only Parquet groups differ from the schema declaration: "
                f"unexpected={unmatched_observed}, missing={unmatched_declared}"
            )
    return complete, tuple(anchor_only)


def _embedded_image(row: Mapping[str, Any]) -> Image.Image:
    value = row["image"]
    if not isinstance(value, dict) or not value.get("bytes"):
        raise ValueError(f"{row['id']}: missing embedded model image")
    with Image.open(io.BytesIO(bytes(value["bytes"]))) as opened:
        return opened.convert("L")


def _thumbnail(row: Mapping[str, Any]) -> Image.Image:
    image = _embedded_image(row)
    fitted = ImageOps.contain(
        image,
        (IMAGE_SIZE, IMAGE_SIZE),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("L", (IMAGE_SIZE, IMAGE_SIZE), 255)
    canvas.paste(
        fitted,
        ((IMAGE_SIZE - fitted.width) // 2, (IMAGE_SIZE - fitted.height) // 2),
    )
    return canvas.convert("RGB")


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.5g}"
    if isinstance(value, list):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    return str(value)


def _delta(row: Mapping[str, Any]) -> dict[str, Any]:
    return _json_object(
        row["parameter_delta_json"],
        field="parameter_delta_json",
        row_id=str(row["id"]),
    )


def _change_lines(
    states: Mapping[int, Mapping[str, Any]],
    slot: int,
) -> list[str]:
    if slot == 0:
        baseline: dict[str, Any] = {}
        for descendant_slot in range(1, 8):
            changes = _delta(states[descendant_slot]).get("changes", {})
            if not isinstance(changes, dict):
                raise ValueError(
                    f"{states[descendant_slot]['id']}: changes is not an object"
                )
            for name, values in changes.items():
                if not isinstance(values, dict) or "before" not in values:
                    raise ValueError(
                        f"{states[descendant_slot]['id']}: malformed change"
                    )
                baseline[str(name)] = values["before"]
        return [
            f"{name}: {_format_value(value)}"
            for name, value in sorted(baseline.items())
        ]

    changes = _delta(states[slot]).get("changes", {})
    if not isinstance(changes, dict) or not changes:
        raise ValueError(f"{states[slot]['id']}: descendant has no changes")
    lines: list[str] = []
    for name, values in sorted(changes.items()):
        if not isinstance(values, dict) or not {"before", "after"} <= set(values):
            raise ValueError(f"{states[slot]['id']}: malformed parameter change")
        lines.append(
            f"{name}: {_format_value(values['before'])} → "
            f"{_format_value(values['after'])}"
        )
    return lines


def _signal(row: Mapping[str, Any]) -> float | None:
    evidence = _json_object(
        row["verification_evidence_json"],
        field="verification_evidence_json",
        row_id=str(row["id"]),
    )
    model_signal = evidence.get("model_input_signal")
    if isinstance(model_signal, dict):
        value = model_signal.get("normalized_changed_fraction")
        if value is not None:
            return float(value)
    mask_delta = evidence.get("mask_delta")
    if isinstance(mask_delta, dict) and mask_delta.get("changed_fraction") is not None:
        return float(mask_delta["changed_fraction"])
    return None


def _fallback_used(row: Mapping[str, Any]) -> bool:
    delta = _delta(row)
    return any(
        bool(delta.get(name))
        for name in ("contract_fallback", "runtime_fallback", "fallback_schedule")
    )


def _range_examples(
    complete: Mapping[str, Mapping[int, Mapping[str, Any]]],
) -> dict[str, dict[str, Any]]:
    signal_records: list[tuple[float, str, int]] = []
    fallback_records: list[tuple[int, str]] = []
    for grammar_id, states in complete.items():
        fallback_count = 0
        for slot in range(1, 8):
            value = _signal(states[slot])
            if value is not None and value > 0.0:
                signal_records.append((value, grammar_id, slot))
            fallback_count += int(_fallback_used(states[slot]))
        if fallback_count:
            fallback_records.append((fallback_count, grammar_id))
    if not signal_records:
        raise ValueError("no descendant contains a visual-difference witness")

    smallest = min(signal_records, key=lambda item: (item[0], item[1], item[2]))
    largest = max(signal_records, key=lambda item: (item[0], item[1], item[2]))
    result = {
        "smallest_visible_change": {
            "grammar_id": smallest[1],
            "realization_id": f"r{smallest[2]:02d}",
            "changed_fraction": smallest[0],
        },
        "largest_visible_change": {
            "grammar_id": largest[1],
            "realization_id": f"r{largest[2]:02d}",
            "changed_fraction": largest[0],
        },
    }
    if fallback_records:
        count, grammar_id = min(
            fallback_records,
            key=lambda item: (-item[0], item[1]),
        )
        result["fallback_example"] = {
            "grammar_id": grammar_id,
            "fallback_realization_count": count,
        }
    return result


def _sheet_for(
    states: Mapping[int, Mapping[str, Any]],
) -> str:
    anchor = states[0]
    level = str(anchor["level"])
    if level == "L0":
        return "01-primitives"
    if level in {"L1", "L2"}:
        return "02-operations-compositions"
    if level == "L3":
        return "03-networks-repeated-media"
    family = str(anchor["family"]).lower()
    structured_terms = (
        "bragg",
        "cavities",
        "edge",
        "grating",
        "mode material",
        "periodic",
        "star",
    )
    if any(term in family for term in structured_terms):
        return "05-structured-photonics"
    return "04-photonic-devices"


def _selection(
    complete: Mapping[str, Mapping[int, Mapping[str, Any]]],
    range_examples: Mapping[str, Mapping[str, Any]],
) -> tuple[dict[str, list[Pick]], dict[str, tuple[str, ...]]]:
    selected = {
        sheet.slug: list(sheet.picks)
        for sheet in SHEETS
    }
    for sheet in SHEETS:
        missing = [
            pick.grammar_id
            for pick in sheet.picks
            if pick.grammar_id not in complete
        ]
        if missing:
            raise ValueError(
                f"{sheet.slug}: curated complete sweeps are missing: {missing}"
            )

    highlights: dict[str, list[str]] = defaultdict(list)
    labels = {
        "smallest_visible_change": "smallest visible change",
        "largest_visible_change": "largest visible change",
        "fallback_example": "fallback path example",
    }
    all_selected = {
        pick.grammar_id
        for picks in selected.values()
        for pick in picks
    }
    for kind, record in range_examples.items():
        grammar_id = str(record["grammar_id"])
        highlights[grammar_id].append(labels[kind])
        if grammar_id in all_selected:
            continue
        slug = _sheet_for(complete[grammar_id])
        selected[slug].append(
            Pick(grammar_id, f"automatically included: {labels[kind]}")
        )
        all_selected.add(grammar_id)
    return selected, {
        grammar_id: tuple(values)
        for grammar_id, values in sorted(highlights.items())
    }


def _fit_font(
    draw: ImageDraw.ImageDraw,
    lines: Sequence[str],
    *,
    maximum: int,
    minimum: int,
    width: int,
) -> ImageFont.ImageFont:
    for size in range(maximum, minimum - 1, -1):
        font = _font(size)
        if all(
            draw.textbbox((0, 0), line, font=font)[2] <= width
            for line in lines
        ):
            return font
    return _font(minimum)


def _wrapped(text: str, width: int) -> list[str]:
    return textwrap.wrap(
        text,
        width=width,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [""]


def _draw_sheet(
    spec: SheetSpec,
    picks: Sequence[Pick],
    complete: Mapping[str, Mapping[int, Mapping[str, Any]]],
    highlights: Mapping[str, Sequence[str]],
) -> Image.Image:
    width = LEFT_WIDTH + len(STATE_SLOTS) * CELL_WIDTH
    height = HEADER_HEIGHT + len(picks) * ROW_HEIGHT
    canvas = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 10), spec.title, fill="black", font=_font(21, bold=True))
    draw.text((16, 39), spec.summary, fill=(70, 70, 70), font=_font(11))
    draw.text(
        (16, 62),
        "Columns are the exact Parquet model images; labels show actual parameter values.",
        fill=(70, 70, 70),
        font=_font(10),
    )

    first_states = complete[picks[0].grammar_id]
    for column, slot in enumerate(STATE_SLOTS):
        row = first_states[slot]
        role = "anchor" if slot == 0 else str(row["transform_kind"]).replace("_", " ")
        x0 = LEFT_WIDTH + column * CELL_WIDTH
        draw.text(
            (x0 + 8, 13),
            f"r{slot:02d}",
            fill=(20, 20, 20),
            font=_font(12, bold=True),
        )
        for line_index, line in enumerate(_wrapped(role, 22)[:2]):
            draw.text(
                (x0 + 8, 34 + line_index * 12),
                line,
                fill=(90, 90, 90),
                font=_font(9),
            )

    for row_index, pick in enumerate(picks):
        states = complete[pick.grammar_id]
        anchor = states[0]
        y0 = HEADER_HEIGHT + row_index * ROW_HEIGHT
        left_fill = (246, 248, 250) if row_index % 2 == 0 else (252, 252, 252)
        draw.rectangle(
            (0, y0, LEFT_WIDTH - 1, y0 + ROW_HEIGHT - 1),
            fill=left_fill,
        )
        label_lines = _wrapped(str(anchor["label"]), 39)[:3]
        y_text = y0 + 10
        for line in label_lines:
            draw.text(
                (12, y_text),
                line,
                fill=(20, 20, 20),
                font=_font(11, bold=True),
            )
            y_text += 15
        draw.text(
            (12, y_text + 3),
            f"{anchor['level']} · {anchor['family']}",
            fill=(70, 70, 70),
            font=_font(9),
        )
        y_text += 20
        for line in _wrapped(pick.rationale, 45)[:2]:
            draw.text(
                (12, y_text + 3),
                line,
                fill=(65, 65, 65),
                font=_font(9),
            )
            y_text += 13
        if pick.grammar_id in highlights:
            y_text += 3
            for value in highlights[pick.grammar_id]:
                draw.rounded_rectangle(
                    (10, y_text, LEFT_WIDTH - 12, y_text + 18),
                    radius=5,
                    fill=(229, 238, 247),
                )
                draw.text(
                    (16, y_text + 3),
                    value,
                    fill=(31, 72, 105),
                    font=_font(9, bold=True),
                )
                y_text += 22
        draw.text(
            (12, y0 + ROW_HEIGHT - 21),
            pick.grammar_id,
            fill=(100, 100, 100),
            font=_font(8),
        )

        for column, slot in enumerate(STATE_SLOTS):
            row = states[slot]
            x0 = LEFT_WIDTH + column * CELL_WIDTH
            if slot == 0:
                draw.rectangle(
                    (x0, y0, x0 + CELL_WIDTH - 1, y0 + ROW_HEIGHT - 1),
                    fill=(248, 248, 248),
                )
            thumb = _thumbnail(row)
            canvas.paste(
                thumb,
                (x0 + (CELL_WIDTH - IMAGE_SIZE) // 2, y0 + 6),
            )
            lines = _change_lines(states, slot)
            font = _fit_font(
                draw,
                lines,
                maximum=8,
                minimum=6,
                width=CELL_WIDTH - 10,
            )
            line_height = max(9, font.size + 2) if hasattr(font, "size") else 10
            text_height = line_height * len(lines)
            available = ROW_HEIGHT - IMAGE_SIZE - 16
            if text_height > available:
                raise ValueError(
                    f"{row['id']}: parameter labels do not fit the review cell"
                )
            y_label = y0 + IMAGE_SIZE + 12
            for line in lines:
                draw.text(
                    (x0 + 5, y_label),
                    line,
                    fill=(25, 25, 25),
                    font=font,
                )
                y_label += line_height
            draw.rectangle(
                (x0, y0, x0 + CELL_WIDTH - 1, y0 + ROW_HEIGHT - 1),
                outline=(214, 218, 222),
                width=1,
            )
        draw.line(
            (0, y0 + ROW_HEIGHT - 1, width, y0 + ROW_HEIGHT - 1),
            fill=(205, 210, 215),
            width=1,
        )
    return canvas


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _review_markdown(manifest: Mapping[str, Any]) -> str:
    lines = [
        "# PixCell depth-v1 visual review",
        "",
        (
            "This pack is generated directly from the depth-v1 Parquet shards. "
            "Every row is one approved representation; r00 is its core anchor "
            "and r01–r07 are controlled geometry realizations. The thumbnails "
            "are the exact images supplied to a model."
        ),
        "",
        (
            "Cell labels are read from `parameter_delta_json`: r00 lists the "
            "anchor values used by the sweep, while each descendant lists every "
            "actual `before → after` parameter change."
        ),
        "",
        "## Sheets",
        "",
        "| Sheet | Scope | Representations |",
        "|---|---|---:|",
    ]
    for sheet in manifest["sheets"]:
        lines.append(
            f"| [{sheet['title']}]({sheet['path']}) | "
            f"{sheet['summary']} | {len(sheet['representations'])} |"
        )

    lines.extend(
        [
            "",
            "## Range checks",
            "",
        ]
    )
    for label, record in manifest["range_examples"].items():
        readable = label.replace("_", " ")
        details = ", ".join(
            f"{key.replace('_', ' ')}={value}"
            for key, value in record.items()
            if key != "grammar_id"
        )
        lines.append(f"- **{readable}:** `{record['grammar_id']}` ({details})")

    lines.extend(
        [
            "",
            "## Selection rationale",
            "",
        ]
    )
    for sheet in manifest["sheets"]:
        lines.extend([f"### {sheet['title']}", ""])
        for record in sheet["representations"]:
            lines.append(
                f"- `{record['grammar_id']}` — {record['rationale']} "
                f"({', '.join(record['controlled_parameters'])})"
            )
        lines.append("")

    anchor_only = manifest["anchor_only_representation_ids"]
    if anchor_only:
        lines.extend(
            [
                "## Anchor-only representations",
                "",
                (
                    "These approved anchors expose no model-observable parameter "
                    "axis and therefore do not appear as padded sweeps:"
                ),
                "",
            ]
        )
        lines.extend(f"- `{grammar_id}`" for grammar_id in anchor_only)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _validate_output_path(root: Path, output: Path) -> None:
    """Keep destructive review output completely outside the PixCell worktree."""

    worktree = root.parents[1]
    if (
        output == worktree
        or output in worktree.parents
        or worktree in output.parents
    ):
        raise ValueError(
            "review output must be outside the PixCell worktree"
        )


def render_review_pack(root: Path, output: Path) -> dict[str, Any]:
    """Render the review-only approval pack and return its manifest."""

    root = root.expanduser().resolve()
    output = output.expanduser().resolve()
    _validate_output_path(root, output)
    rows, shard_paths = _load_rows(root)
    complete, anchor_only = _group_sweeps(rows)
    range_examples = _range_examples(complete)
    selections, highlights = _selection(complete, range_examples)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{output.name}-", dir=output.parent)
    )
    try:
        sheet_records: list[dict[str, Any]] = []
        for spec in SHEETS:
            picks = selections[spec.slug]
            image = _draw_sheet(spec, picks, complete, highlights)
            filename = f"{spec.slug}.png"
            path = temporary / filename
            image.save(
                path,
                format="PNG",
                optimize=False,
                compress_level=PNG_COMPRESSION,
            )
            representations = []
            for pick in picks:
                states = complete[pick.grammar_id]
                controlled = sorted(
                    {
                        name
                        for slot in range(1, 8)
                        for name in _delta(states[slot]).get("changes", {})
                    }
                )
                representations.append(
                    {
                        "grammar_id": pick.grammar_id,
                        "label": str(states[0]["label"]),
                        "level": str(states[0]["level"]),
                        "family": str(states[0]["family"]),
                        "rationale": pick.rationale,
                        "controlled_parameters": controlled,
                        "highlights": list(highlights.get(pick.grammar_id, ())),
                    }
                )
            sheet_records.append(
                {
                    "path": filename,
                    "sha256": _sha256_file(path),
                    "title": spec.title,
                    "summary": spec.summary,
                    "representations": representations,
                }
            )

        shard_records = [
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256_file(path),
            }
            for path in shard_paths
        ]
        manifest: dict[str, Any] = {
            "schema_version": "pixcell-depth-review-pack-v1",
            "source_parquet_shards": shard_records,
            "state_slots": [f"r{slot:02d}" for slot in STATE_SLOTS],
            "complete_sweep_count": len(complete),
            "anchor_only_representation_ids": list(anchor_only),
            "range_examples": range_examples,
            "sheets": sheet_records,
        }
        (temporary / "manifest.json").write_text(
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
        (temporary / "REVIEW.md").write_text(
            _review_markdown(manifest),
            encoding="utf-8",
        )
        if output.exists():
            shutil.rmtree(output)
        temporary.replace(output)
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="depth-v1 release root",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="review-only output directory outside the depth-v1 release root",
    )
    args = parser.parse_args()
    manifest = render_review_pack(args.root, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output.expanduser().resolve()),
                "sheet_count": len(manifest["sheets"]),
                "selected_representation_count": sum(
                    len(sheet["representations"])
                    for sheet in manifest["sheets"]
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
