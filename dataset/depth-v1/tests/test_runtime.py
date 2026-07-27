from __future__ import annotations

import copy
import importlib.util
import io
import re
import sys
from pathlib import Path

import pyarrow.parquet as pq
import pytest
from PIL import Image


DATASET_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_PATH = DATASET_ROOT / "depth-v1" / "scripts" / "runtime.py"
SPEC = importlib.util.spec_from_file_location("pixcell_depth_runtime", RUNTIME_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime
SPEC.loader.exec_module(runtime)


REPRESENTATIVE_IDS = {
    "l0": "l0_01_rectangle__semantic__square",
    "l1": "l1_01_translate__a1__proposal_a",
    "l2": "l2_01_mirrored_fixed_gap_pair__s01__proposal_b",
    "l3": "l3_01_serial_heterogeneous_chain_s01",
    "l4": "y_branch_smooth_1x2",
}


def _row(level: str, example_id: str) -> dict:
    path = next((DATASET_ROOT / "data" / level).glob("train-*.parquet"))
    rows = pq.read_table(path).to_pylist()
    return next(row for row in rows if row["id"] == example_id)


def _polygon(
    exterior: list[list[float]],
    *,
    holes: list[list[list[float]]] | None = None,
) -> dict:
    return {
        "layer": [1, 0],
        "exterior": exterior,
        "holes": holes or [],
    }


def _runtime_record(polygons: list[dict]) -> dict:
    geometry = runtime._geometry_from_polygons(polygons)
    min_x, min_y, max_x, max_y = geometry.bounds
    bbox = [
        [runtime._round_float(min_x), runtime._round_float(min_y)],
        [runtime._round_float(max_x), runtime._round_float(max_y)],
    ]
    return {
        "bbox_um": bbox,
        "bbox_span_um": [
            runtime._round_float(max_x - min_x),
            runtime._round_float(max_y - min_y),
        ],
        "edge_material_intervals": runtime._edge_intervals_for_geometry(
            geometry,
            (min_x, min_y, max_x, max_y),
        ),
        "polygons": polygons,
        "ports": [],
        "structural_metrics": {
            "primitive_call_histogram": {},
            "reference_operation_histogram": {},
            **runtime._geometry_metrics(geometry, polygons),
        },
    }


@pytest.mark.parametrize("level", sorted(REPRESENTATIVE_IDS))
def test_execution_rendering_and_port_gate_across_curriculum(level: str) -> None:
    row = _row(level, REPRESENTATIVE_IDS[level])
    result = runtime.execute_program(row["code"], isolation="in_process")

    assert result["structural_metrics"]["polygon_count"] == len(result["polygons"])
    assert result["structural_metrics"]["material_area_um2"] > 0
    assert runtime.gate_ports(result).passed

    views = runtime.render_views(
        result,
        maximum_canvas_px=(320, 320),
        physical_long_edge_px=480,
        margin_px=20,
    )
    assert views["maximum_visibility"].canvas_px == (320, 320)
    physical_scale = views["physical_aspect"].scale_px_per_um
    assert physical_scale[0] == physical_scale[1]
    for view in views.values():
        with Image.open(io.BytesIO(view.png_bytes)) as opened:
            assert opened.mode == "L"
            assert opened.getextrema() == (0, 255)


def test_subprocess_execution_smoke() -> None:
    row = _row("l0", REPRESENTATIVE_IDS["l0"])
    result = runtime.execute_program(
        row["code"],
        isolation="subprocess",
        timeout_seconds=30,
    )
    assert result["bbox_span_um"] == [22.0, 22.0]


def test_rotated_reference_uses_material_not_instance_bbox() -> None:
    row = _row("l0", "l0_04_cross__equivariance__medium_rot45")
    result = runtime.execute_program(row["code"], isolation="in_process")
    assert result["bbox_span_um"] == pytest.approx(row["footprint_um"], abs=0.0021)
    assert result["bbox_span_um"][0] == pytest.approx(23.3345, abs=0.0021)


def test_ring_runtime_reports_union_visible_hole() -> None:
    row = _row("l0", "l0_03_ring__semantic__medium_wall")
    result = runtime.execute_program(row["code"], isolation="in_process")
    assert result["structural_metrics"]["hole_count"] == 1


def test_tight_smoothed_path_ignores_subresolution_union_holes() -> None:
    row = _row("l0", "l0_20_path_smooth__semantic__tight_corner")
    result = runtime.execute_program(row["code"], isolation="in_process")
    assert result["structural_metrics"]["hole_count"] == 0


def test_hole_metric_uses_visible_area_floor() -> None:
    subresolution = _runtime_record(
        [
            _polygon(
                [[0, 0], [10, 0], [10, 10], [0, 10]],
                holes=[
                    [
                        [4.999, 4.999],
                        [4.999, 5.001],
                        [5.001, 5.001],
                        [5.001, 4.999],
                    ]
                ],
            )
        ]
    )
    assert subresolution["structural_metrics"]["hole_count"] == 0

    visible = _runtime_record(
        [
            _polygon(
                [[0, 0], [10, 0], [10, 10], [0, 10]],
                holes=[
                    [
                        [4.99, 4.99],
                        [4.99, 5.01],
                        [5.01, 5.01],
                        [5.01, 4.99],
                    ]
                ],
            )
        ]
    )
    assert visible["structural_metrics"]["hole_count"] == 1


def test_union_metrics_count_created_and_filled_holes() -> None:
    frame = [
        _polygon([[0, 0], [10, 0], [10, 2], [0, 2]]),
        _polygon([[0, 8], [10, 8], [10, 10], [0, 10]]),
        _polygon([[0, 2], [2, 2], [2, 8], [0, 8]]),
        _polygon([[8, 2], [10, 2], [10, 8], [8, 8]]),
    ]
    frame_record = _runtime_record(frame)
    assert frame_record["structural_metrics"]["connected_component_count"] == 1
    assert frame_record["structural_metrics"]["hole_count"] == 1

    annulus_and_fill = [
        _polygon(
            [[0, 0], [10, 0], [10, 10], [0, 10]],
            holes=[[[2, 2], [2, 8], [8, 8], [8, 2]]],
        ),
        _polygon([[2, 2], [8, 2], [8, 8], [2, 8]]),
    ]
    filled_record = _runtime_record(annulus_and_fill)
    assert filled_record["structural_metrics"]["hole_count"] == 0


def test_nonrepeat_candidate_cannot_change_visible_hole_count() -> None:
    frame = [
        _polygon([[0, 0], [10, 0], [10, 2], [0, 2]]),
        _polygon([[0, 8], [10, 8], [10, 10], [0, 10]]),
        _polygon([[0, 2], [2, 2], [2, 8], [0, 8]]),
        _polygon([[8, 2], [10, 2], [10, 8], [8, 8]]),
    ]
    reference = _runtime_record(frame)
    candidate = _runtime_record(
        [*frame, _polygon([[2, 2], [8, 2], [8, 8], [2, 8]])]
    )
    report = runtime.validate_candidate(reference, candidate)
    assert not report.passed
    assert report.structural_deltas["hole_count"] == (1, 0)
    assert runtime.validate_candidate(
        reference,
        candidate,
        require_same_holes=False,
    ).passed


def test_polygon_only_material_bounds_ignore_zero_width_spike() -> None:
    spike = _polygon(
        [[0, 0], [2, 0], [2, 2], [1, 2], [1, 3], [1, 2], [0, 2]]
    )
    geometry = runtime._geometry_from_polygons([spike])
    assert geometry.bounds == (0.0, 0.0, 2.0, 2.0)
    assert geometry.area == pytest.approx(4.0)


def test_runtime_record_rejects_bbox_not_bound_to_material() -> None:
    record = _runtime_record(
        [_polygon([[0, 0], [10, 0], [10, 2], [0, 2]])]
    )
    runtime._validate_runtime_record(record)
    stale = copy.deepcopy(record)
    stale["bbox_um"] = [[0.0, 0.0], [100.0, 100.0]]
    stale["bbox_span_um"] = [100.0, 100.0]
    with pytest.raises(runtime.RuntimeGateError, match="material polygon bounds"):
        runtime._validate_runtime_record(stale)


def test_shared_frame_delta_detects_controlled_parameter_change() -> None:
    row = _row("l0", REPRESENTATIVE_IDS["l0"])
    candidate_source = row["code"].replace(
        "length_um = 22.0",
        "length_um = 30.0",
        1,
    )
    assert candidate_source != row["code"]
    anchor = runtime.execute_program(row["code"], isolation="in_process")
    candidate = runtime.execute_program(candidate_source, isolation="in_process")

    delta = runtime.compare_masks(
        anchor,
        candidate,
        mode="physical_aspect",
        physical_long_edge_px=600,
    )
    assert 0.0 < delta.changed_fraction < 1.0
    assert 0.0 < delta.iou < 1.0
    assert runtime.validate_candidate(anchor, candidate).passed


def test_renderer_preserves_islands_inside_another_polygons_hole() -> None:
    annulus = {
        "layer": [1, 0],
        "exterior": [[0, 0], [10, 0], [10, 10], [0, 10]],
        "holes": [[[2, 2], [2, 8], [8, 8], [8, 2]]],
    }
    island = {
        "layer": [1, 0],
        "exterior": [[4, 4], [6, 4], [6, 6], [4, 6]],
        "holes": [],
    }
    record = _runtime_record([annulus, island])
    rendered = runtime.render_geometry(
        record,
        mode="physical_aspect",
        physical_long_edge_px=220,
        margin_px=10,
    )
    mask = runtime.png_mask(rendered.png_bytes)
    assert mask[mask.shape[0] // 2, mask.shape[1] // 2]
    assert not mask[mask.shape[0] // 2, 70]

    reversed_record = {**record, "polygons": list(reversed(record["polygons"]))}
    reversed_render = runtime.render_geometry(
        reversed_record,
        mode="physical_aspect",
        physical_long_edge_px=220,
        margin_px=10,
    )
    assert reversed_render.png_bytes == rendered.png_bytes


def test_boundary_derived_specs_round_trip_every_l4_anchor() -> None:
    path = next((DATASET_ROOT / "data" / "l4").glob("train-*.parquet"))
    rows = pq.read_table(path).to_pylist()
    for row in rows:
        result = runtime.execute_program(row["code"], isolation="in_process")
        derived = runtime.derive_optical_port_specs(result, result)
        observed = tuple(
            (
                port["name"],
                tuple(port["center"]),
                port["width"],
                port["orientation"],
            )
            for port in result["ports"]
        )
        assert derived == observed, row["id"]


def test_boundary_specs_repair_a_changed_l4_body() -> None:
    row = _row("l4", REPRESENTATIVE_IDS["l4"])
    anchor = runtime.execute_program(row["code"], isolation="in_process")
    mutated_source = row["code"].replace(
        "branch_length_um = 22.0",
        "branch_length_um = 27.0",
        1,
    )
    stale = runtime.execute_program(mutated_source, isolation="in_process")
    assert not runtime.gate_ports(
        stale,
        reference=anchor,
        require_bbox_edge=True,
    ).passed

    derived = runtime.derive_optical_port_specs(anchor, stale)
    repaired_source = re.sub(
        r"^optical_port_specs = .*$",
        f"optical_port_specs = {derived!r}",
        mutated_source,
        count=1,
        flags=re.MULTILINE,
    )
    repaired = runtime.execute_program(repaired_source, isolation="in_process")
    assert runtime.gate_ports(
        repaired,
        reference=anchor,
        require_bbox_edge=True,
    ).passed
    assert derived[1][1][0] == 50.0
    assert derived[2][1][0] == 50.0


def test_port_contact_gate_rejects_detached_terminal() -> None:
    row = _row("l4", REPRESENTATIVE_IDS["l4"])
    anchor = runtime.execute_program(row["code"], isolation="in_process")
    detached = copy.deepcopy(anchor)
    detached["ports"][0]["center"][1] += 50.0
    report = runtime.gate_ports(detached, reference=anchor)
    assert not report.passed
    assert any("inward material fraction" in error for error in report.errors)


def test_runtime_rejects_non_catalog_execution_import() -> None:
    source = """
import os
import gdsfactory as gf

@gf.cell(check_instances=False)
def device():
    return gf.components.rectangle(size=(10, 2))
"""
    with pytest.raises(runtime.RuntimeGateError, match="runtime import"):
        runtime.execute_program(source, isolation="in_process")
