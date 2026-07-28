"""Parametric primitives-only recreation of the final7 perforated racetrack."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


LAYER = (1, 0)

# Overall annular frame.
outer_length = 3.0
outer_width = 5.5
ring_side_width = 0.31
ring_cap_width = 0.52
ring_top_straight = 0.90
ring_side_straight = 1.30
ring_curve_control_x = 0.52
ring_curve_control_y = 2.08
ring_join_overlap = 0.01

# Mirrored perforated bridges.
bridge_body_length = 0.886
bridge_body_height = 1.03
bridge_center_offset = 0.915
bridge_arm_width = 0.43
bridge_branch_width = 0.21
bridge_arm_run = 0.33
bridge_arm_rise = 0.915
bridge_join_x = 1.19

# Two rectangular air slots in each bridge body.
slot_length = 0.329
slot_height = 0.56
slot_pitch = 0.438

# Live function knob: material loading tooth into the upper-left slot.
transfer_length = 0.020
slot_base_extension = 0.020


def _cubic_path(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    samples: int = 81,
) -> gf.Path:
    """Return a sampled cubic Bezier as an allowed parametric gf.Path."""
    t = np.linspace(0.0, 1.0, samples)[:, None]
    points = (
        (1.0 - t) ** 3 * np.asarray(p0)
        + 3.0 * (1.0 - t) ** 2 * t * np.asarray(p1)
        + 3.0 * (1.0 - t) * t**2 * np.asarray(p2)
        + t**3 * np.asarray(p3)
    )
    return gf.Path(points)


def _path_component(
    points: list[tuple[float, float]],
    width: float,
) -> gf.Component:
    path = gf.Path(np.asarray(points))
    return gf.path.extrude(path, width=width, layer=LAYER)


def _transition_component(
    path: gf.Path,
    width_start: float,
    width_end: float,
) -> gf.Component:
    cross_section_start = gf.cross_section.cross_section(
        width=width_start,
        layer=LAYER,
    )
    cross_section_end = gf.cross_section.cross_section(
        width=width_end,
        layer=LAYER,
    )
    transition = gf.path.transition(
        cross_section_start,
        cross_section_end,
        width_type=_edge_weighted_width,
    )
    return gf.path.extrude_transition(path, transition)


def _edge_weighted_width(
    position: np.ndarray,
    width_start: float,
    width_end: float,
) -> np.ndarray:
    """Keep the narrow side width through most of each curved quadrant."""
    if width_start > width_end:
        return width_end + (width_start - width_end) * (1.0 - position) ** 3
    return width_start + (width_end - width_start) * position**3


def _centered_rectangle(
    width: float,
    height: float,
    center_x: float,
    center_y: float,
) -> gf.Component:
    component = gf.Component()
    rectangle = component << gf.components.rectangle(
        size=(width, height),
        layer=LAYER,
        centered=True,
    )
    rectangle.dmove((center_x, center_y))
    return component


def _outer_loop() -> gf.Component:
    """Build the variable-width closed oval from straights and Bezier paths."""
    top_y = outer_width / 2.0 - ring_cap_width / 2.0
    side_x = outer_length / 2.0 - ring_side_width / 2.0
    top_half = ring_top_straight / 2.0
    side_half = ring_side_straight / 2.0

    pieces = gf.Component()
    pieces.add_ref(
        _path_component(
            [
                (-top_half - ring_join_overlap, top_y),
                (top_half + ring_join_overlap, top_y),
            ],
            ring_cap_width,
        )
    )
    pieces.add_ref(
        _path_component(
            [
                (top_half + ring_join_overlap, -top_y),
                (-top_half - ring_join_overlap, -top_y),
            ],
            ring_cap_width,
        )
    )
    pieces.add_ref(
        _path_component(
            [
                (side_x, side_half + ring_join_overlap),
                (side_x, -side_half - ring_join_overlap),
            ],
            ring_side_width,
        )
    )
    pieces.add_ref(
        _path_component(
            [
                (-side_x, -side_half - ring_join_overlap),
                (-side_x, side_half + ring_join_overlap),
            ],
            ring_side_width,
        )
    )

    top_right = _cubic_path(
        (top_half, top_y),
        (ring_curve_control_x, top_y),
        (side_x, ring_curve_control_y),
        (side_x, side_half),
    )
    top_left = _cubic_path(
        (-top_half, top_y),
        (-ring_curve_control_x, top_y),
        (-side_x, ring_curve_control_y),
        (-side_x, side_half),
    )
    bottom_right = _cubic_path(
        (side_x, -side_half),
        (side_x, -ring_curve_control_y),
        (ring_curve_control_x, -top_y),
        (top_half, -top_y),
    )
    bottom_left = _cubic_path(
        (-side_x, -side_half),
        (-side_x, -ring_curve_control_y),
        (-ring_curve_control_x, -top_y),
        (-top_half, -top_y),
    )
    pieces.add_ref(
        _transition_component(top_right, ring_cap_width, ring_side_width)
    )
    pieces.add_ref(
        _transition_component(top_left, ring_cap_width, ring_side_width)
    )
    pieces.add_ref(
        _transition_component(bottom_right, ring_side_width, ring_cap_width)
    )
    pieces.add_ref(
        _transition_component(bottom_left, ring_side_width, ring_cap_width)
    )
    return pieces


def _bridge_material() -> gf.Component:
    """Build both bridge bodies and their four oblique joining arms."""
    material = gf.Component()
    for sign_y in (1.0, -1.0):
        body_y = sign_y * bridge_center_offset
        material.add_ref(
            _centered_rectangle(
                bridge_body_length,
                bridge_body_height,
                0.0,
                body_y,
            )
        )
        for sign_x in (-1.0, 1.0):
            inner_x = sign_x * bridge_body_length / 2.0
            elbow_x = sign_x * (bridge_body_length / 2.0 + bridge_arm_run)
            join_x = sign_x * bridge_join_x
            material.add_ref(
                _path_component(
                    [(inner_x, body_y), (elbow_x, body_y)],
                    bridge_arm_width,
                )
            )
            material.add_ref(
                _path_component(
                    [
                        (elbow_x, body_y),
                        (
                            join_x,
                            sign_y * (bridge_center_offset - bridge_arm_rise),
                        ),
                    ],
                    bridge_branch_width,
                )
            )
    return material


def _slot_cuts() -> gf.Component:
    """Build the four air-slot primitives before the loading tooth is restored."""
    cuts = gf.Component()
    left_center = -slot_pitch / 2.0
    right_center = slot_pitch / 2.0

    # The upper-left base cut is longer by transfer_length. The material tooth
    # is restored after subtraction, making the live area response exact.
    upper_y = bridge_center_offset
    upper_left_start = left_center - slot_length / 2.0 - slot_base_extension
    upper_left_end = left_center + slot_length / 2.0
    cuts.add_ref(
        _centered_rectangle(
            upper_left_end - upper_left_start,
            slot_height,
            (upper_left_start + upper_left_end) / 2.0,
            upper_y,
        )
    )

    cuts.add_ref(
        _centered_rectangle(
            slot_length,
            slot_height,
            right_center,
            upper_y,
        )
    )
    lower_y = -bridge_center_offset
    cuts.add_ref(
        _centered_rectangle(
            slot_length,
            slot_height,
            left_center,
            lower_y,
        )
    )
    cuts.add_ref(
        _centered_rectangle(
            slot_length,
            slot_height,
            right_center,
            lower_y,
        )
    )
    return cuts


def _transfer_tooth() -> tuple[gf.Component, gf.Path]:
    """Restore a path-extruded loading tooth into the upper-left slot."""
    left_center = -slot_pitch / 2.0
    start_x = left_center - slot_length / 2.0 - slot_base_extension
    tooth_path = gf.Path(
        np.asarray(
            [
                (start_x, bridge_center_offset),
                (start_x + transfer_length, bridge_center_offset),
            ]
        )
    )
    tooth = gf.path.extrude(tooth_path, width=slot_height, layer=LAYER)
    return tooth, tooth_path


def _loading_measurement_paths() -> tuple[gf.Path, gf.Path]:
    """Return live centerlines for the fixed datum and loaded material tooth."""
    body_left = -bridge_body_length / 2.0
    base_frame_length = (
        bridge_body_length / 2.0
        - slot_pitch / 2.0
        - slot_length / 2.0
        - slot_base_extension
    )
    reference_path = gf.Path(
        np.asarray(
            [
                (body_left, bridge_center_offset),
                (body_left + base_frame_length, bridge_center_offset),
            ]
        )
    )
    loaded_path = gf.Path(
        np.asarray(
            [
                (body_left, bridge_center_offset),
                (
                    body_left + base_frame_length + transfer_length,
                    bridge_center_offset,
                ),
            ]
        )
    )
    return reference_path, loaded_path


@gf.cell
def build_device() -> gf.Component:
    """Assemble the connected perforated racetrack on layer (1, 0)."""
    unperforated = gf.Component()
    unperforated.add_ref(_outer_loop())
    unperforated.add_ref(_bridge_material())

    perforated = gf.boolean(
        unperforated,
        _slot_cuts(),
        operation="not",
        layer=LAYER,
    )
    tooth, _ = _transfer_tooth()
    final_geometry = gf.boolean(
        perforated,
        tooth,
        operation="or",
        layer=LAYER,
    )
    footprint_clip = _centered_rectangle(
        outer_length,
        outer_width,
        0.0,
        0.0,
    )
    clipped_geometry = gf.boolean(
        final_geometry,
        footprint_clip,
        operation="and",
        layer=LAYER,
    )

    component = gf.Component()
    component.add_ref(clipped_geometry)
    return component


if __name__ == "__main__":
    output_directory = Path(__file__).resolve().parent
    reference_loading_path, active_loading_path = _loading_measurement_paths()
    reference_length = float(
        np.linalg.norm(np.diff(reference_loading_path.points, axis=0), axis=1).sum()
    )
    active_length = float(
        np.linalg.norm(np.diff(active_loading_path.points, axis=0), axis=1).sum()
    )
    measured_transfer_length = abs(active_length - reference_length)
    lengths = {
        "arms": {
            "reference_loading_path": reference_length,
            "active_loading_path": active_length,
        },
        "delta_length_um": measured_transfer_length,
    }
    (output_directory / "lengths.json").write_text(
        json.dumps(lengths, indent=2) + "\n"
    )
    build_device().write_gds(
        output_directory / "device.gds",
        with_metadata=False,
    )
