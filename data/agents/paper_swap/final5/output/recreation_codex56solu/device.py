"""Parametric primitive-only reconstruction of a dual-sided SWG coupler."""

from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Fabrication layer.
layer = (1, 0)

# Central bus: this live length knob is also used for geometry-response proof.
bus_start = 1.91
bus_length = 14.06
central_bus_width = 0.024
bus_y = 0.357

# Coupling region and subwavelength-grating controls.
transfer_length = 8.70
grating_start = 4.45
grating_cell_count = 56
grating_period = 0.160
grating_chirp_depth = 0.017
grating_chirp_sigma = 2.4
grating_fill_factor = 0.72
grating_rail_width = 0.052
coupling_gap = 0.017
axial_gap = 0.035

# Folded auxiliary-guide controls.
outer_rail_width = 0.064
fold_radius_x = 1.235
fold_asymmetry_x = -0.055
fold_radius_y = 0.126
right_fold_center_x = 14.05
left_fold_center_x = 4.04

# Straight and curved fanout/taper controls.
straight_taper_length = 1.53
straight_tip_width = 0.004
top_straight_taper_tip_x = 2.22
bottom_straight_taper_full_x = 14.10
curved_taper_length = 4.47
curved_taper_skew = 0.055
curved_tip_width = 0.038
curved_fanout_drop = 0.274
curved_decay_length = 0.78
bottom_frame_tail = 0.0135


def _path(points: np.ndarray | list[tuple[float, float]]) -> gf.Path:
    """Return a GDSFactory path from sampled centerline points."""
    return gf.Path(np.asarray(points, dtype=float))


def _constant_extrusion(points: np.ndarray | list[tuple[float, float]], width: float):
    """Extrude one constant-width primitive path."""
    return gf.path.extrude(_path(points), width=width, layer=layer)


def _transition_extrusion(
    points: np.ndarray | list[tuple[float, float]],
    width1: float,
    width2: float,
):
    """Extrude one path with a smooth width transition."""
    xs1 = gf.cross_section.cross_section(width=width1, layer=layer, radius=None)
    xs2 = gf.cross_section.cross_section(width=width2, layer=layer, radius=None)
    transition = gf.path.transition(xs1, xs2, width_type="sine")
    return gf.path.extrude_transition(_path(points), transition)


def _top_fold_points(y_inner: float, y_outer: float) -> np.ndarray:
    """Half-ellipse taking the upper inner rail into its left-going return."""
    theta = np.linspace(0.0, math.pi, 181)
    radius_x = fold_radius_x + fold_asymmetry_x
    center_y = 0.5 * (y_inner + y_outer)
    radius_y = 0.5 * (y_outer - y_inner)
    return np.column_stack(
        (
            right_fold_center_x + radius_x * np.sin(theta),
            center_y - radius_y * np.cos(theta),
        )
    )


def _bottom_fold_points(y_inner: float, y_outer: float) -> np.ndarray:
    """Half-ellipse taking the lower inner rail into its right-going return."""
    theta = np.linspace(0.0, math.pi, 181)
    radius_x = fold_radius_x - fold_asymmetry_x
    center_y = 0.5 * (y_inner + y_outer)
    radius_y = 0.5 * (y_inner - y_outer)
    return np.column_stack(
        (
            left_fold_center_x - radius_x * np.sin(theta),
            center_y + radius_y * np.cos(theta),
        )
    )


def _curved_fanout_points(
    x_start: float,
    x_end: float,
    y_start: float,
    y_end: float,
    reverse_decay: bool,
) -> np.ndarray:
    """Sample a monotone exponential fanout with horizontal inner tangent."""
    count = 241
    x = np.linspace(x_start, x_end, count)
    length = x_end - x_start
    s = x - x_start
    normalizer = 1.0 - math.exp(-length / curved_decay_length)
    if reverse_decay:
        fraction = (
            np.exp(-(length - s) / curved_decay_length)
            - math.exp(-length / curved_decay_length)
        ) / normalizer
    else:
        fraction = (
            np.exp(-s / curved_decay_length)
            - math.exp(-length / curved_decay_length)
        ) / normalizer
    if reverse_decay:
        y = y_start + (y_end - y_start) * fraction
    else:
        y = y_end + (y_start - y_end) * fraction
    return np.column_stack((x, y))


def _grating_centers(segment_length: float) -> list[float]:
    """Generate a symmetric two-lobe chirped sequence over transfer_length."""
    raw = [0.0]
    for index in range(grating_cell_count - 1):
        compression = math.exp(
            -0.5 * ((index - 25.5) / grating_chirp_sigma) ** 2
        ) + math.exp(-0.5 * ((index - 41.5) / grating_chirp_sigma) ** 2)
        local_period = grating_period - grating_chirp_depth * compression
        raw.append(raw[-1] + local_period)

    available_center_span = transfer_length - segment_length
    raw_span = raw[-1]
    scale = available_center_span / raw_span
    return [
        grating_start + 0.5 * segment_length + value * scale for value in raw
    ]


@gf.cell
def build_device() -> gf.Component:
    """Assemble the coupler from path, taper, and rectangle primitives."""
    component = gf.Component()

    top_grating_y = (
        bus_y + 0.5 * central_bus_width + coupling_gap + 0.5 * grating_rail_width
    )
    bottom_grating_y = (
        bus_y - 0.5 * central_bus_width - coupling_gap - 0.5 * grating_rail_width
    )
    top_outer_y = top_grating_y + 2.0 * fold_radius_y
    bottom_outer_y = bottom_grating_y - 2.0 * fold_radius_y
    grating_end = grating_start + transfer_length

    # Continuous narrow center guide.
    bus_path = _path(
        [(bus_start, bus_y), (bus_start + bus_length, bus_y)]
    )
    component.add_ref(
        gf.path.extrude(bus_path, width=central_bus_width, layer=layer)
    )

    # Two identical segmented coupling rails.
    segment_length = grating_period * grating_fill_factor
    segment = gf.components.rectangle(
        size=(segment_length, grating_rail_width),
        layer=layer,
        centered=False,
        port_orientations=None,
    )
    for center_x in _grating_centers(segment_length):
        for center_y in (top_grating_y, bottom_grating_y):
            reference = component.add_ref(segment)
            reference.dmove(
                (
                    center_x - 0.5 * segment_length,
                    center_y - 0.5 * grating_rail_width,
                )
            )

    # Upper left curved fanout into the first segmented rail.
    top_curved_end_x = grating_start - axial_gap
    top_curved_length = curved_taper_length - curved_taper_skew
    top_curved_start_x = top_curved_end_x - top_curved_length
    top_curved_points = _curved_fanout_points(
        top_curved_start_x,
        top_curved_end_x,
        top_grating_y + curved_fanout_drop,
        top_grating_y,
        reverse_decay=False,
    )
    component.add_ref(
        _transition_extrusion(
            top_curved_points, curved_tip_width, grating_rail_width
        )
    )

    # Upper right fold, return rail, and straight inverse taper.
    component.add_ref(
        _constant_extrusion(
            [
                (grating_end + axial_gap, top_grating_y),
                (right_fold_center_x, top_grating_y),
            ],
            grating_rail_width,
        )
    )
    component.add_ref(
        _transition_extrusion(
            _top_fold_points(top_grating_y, top_outer_y),
            grating_rail_width,
            outer_rail_width,
        )
    )
    top_taper_full_x = top_straight_taper_tip_x + straight_taper_length
    component.add_ref(
        _constant_extrusion(
            [
                (right_fold_center_x, top_outer_y),
                (top_taper_full_x, top_outer_y),
            ],
            outer_rail_width,
        )
    )
    component.add_ref(
        _transition_extrusion(
            [
                (top_straight_taper_tip_x, top_outer_y),
                (top_taper_full_x, top_outer_y),
            ],
            straight_tip_width,
            outer_rail_width,
        )
    )

    # Lower left fold, return rail, and straight inverse taper.
    component.add_ref(
        _constant_extrusion(
            [
                (grating_start - axial_gap, bottom_grating_y),
                (left_fold_center_x, bottom_grating_y),
            ],
            grating_rail_width,
        )
    )
    component.add_ref(
        _transition_extrusion(
            _bottom_fold_points(bottom_grating_y, bottom_outer_y),
            grating_rail_width,
            outer_rail_width,
        )
    )
    component.add_ref(
        _constant_extrusion(
            [
                (left_fold_center_x, bottom_outer_y),
                (bottom_straight_taper_full_x, bottom_outer_y),
            ],
            outer_rail_width,
        )
    )
    component.add_ref(
        _transition_extrusion(
            [
                (bottom_straight_taper_full_x, bottom_outer_y),
                (
                    bottom_straight_taper_full_x + straight_taper_length,
                    bottom_outer_y,
                ),
            ],
            outer_rail_width,
            straight_tip_width,
        )
    )

    # Lower right curved fanout out of the second segmented rail.
    bottom_curved_start_x = grating_end + axial_gap
    bottom_curved_length = curved_taper_length + curved_taper_skew
    bottom_curved_end_x = bottom_curved_start_x + bottom_curved_length
    bottom_curved_points = _curved_fanout_points(
        bottom_curved_start_x,
        bottom_curved_end_x,
        bottom_grating_y,
        bottom_grating_y - curved_fanout_drop - bottom_frame_tail,
        reverse_decay=True,
    )
    component.add_ref(
        _transition_extrusion(
            bottom_curved_points, grating_rail_width, curved_tip_width
        )
    )

    # The measurement contract records two real centerline objects.
    grating_axis = _path(
        [
            (grating_start, top_grating_y),
            (grating_start + transfer_length, top_grating_y),
        ]
    )
    arm_lengths = {
        "center_bus": float(bus_path.length()),
        "segmented_axis": float(grating_axis.length()),
    }
    measured_delta = abs(arm_lengths["center_bus"] - arm_lengths["segmented_axis"])
    lengths_path = Path(__file__).with_name("lengths.json")
    lengths_path.write_text(
        json.dumps(
            {
                "arms": arm_lengths,
                "delta_length_um": measured_delta,
                "coupler": {
                    "length_um": float(grating_axis.length()),
                    "gap_um": coupling_gap,
                    "width_um": grating_rail_width,
                },
            },
            indent=2,
        )
    )

    return component


device = build_device()
device.write_gds(Path(__file__).with_name("device.gds"), with_metadata=False)
