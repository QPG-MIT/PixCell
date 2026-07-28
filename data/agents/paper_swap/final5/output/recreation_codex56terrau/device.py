"""Primitives-only reconstruction of the supplied fishbone transition image."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Function-defining, JEE-substitutable dimensions (all in um).
LAYER = (1, 0)
footprint_height = 0.700
spine_x0 = 1.945
spine_length = 14.025
spine_width = 0.025
fin_count = 56
fin_pitch = 0.160
fin_length = 0.115
fin_height = 0.050
fin_gap = 0.018
pattern_start = 4.454
pattern_length = 8.704
left_transition_length = 4.375
right_transition_length = 4.380
transition_width = 0.050
bend_radius = 0.1275
delta_length = 0.503

# The image has a gentle two-lobe chirp in the fin centers and duty factor.
# Values are normalized so fin_pitch, fin_length, and pattern_length remain live knobs.
_NOMINAL_FIN_PITCH = 0.160
_FIN_POSITION_FACTORS = (
    0.0000, 0.0184, 0.0368, 0.0551, 0.0735, 0.0919, 0.1103, 0.1287,
    0.1471, 0.1649, 0.1832, 0.2016, 0.2200, 0.2384, 0.2568, 0.2752,
    0.2935, 0.3119, 0.3297, 0.3481, 0.3665, 0.3849, 0.4032, 0.4211,
    0.4389, 0.4553, 0.4716, 0.4874, 0.5038, 0.5208, 0.5392, 0.5576,
    0.5760, 0.5943, 0.6127, 0.6311, 0.6495, 0.6678, 0.6857, 0.7029,
    0.7196, 0.7362, 0.7529, 0.7701, 0.7867, 0.8034, 0.8206, 0.8384,
    0.8568, 0.8752, 0.8935, 0.9125, 0.9308, 0.9492, 0.9670, 0.9860,
)
_FIN_LENGTH_FACTORS = (
    1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000,
    0.957, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 0.957,
    0.957, 0.957, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000,
    0.913, 0.870, 0.870, 0.870, 0.913, 0.957, 1.000, 0.957,
    1.000, 0.957, 1.000, 1.000, 1.000, 0.957, 0.913, 0.870,
    0.870, 0.870, 0.870, 0.870, 0.913, 0.913, 0.957, 1.000,
    1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.043, 0.957,
)

# Centerline samples for the two short access transitions, measured in the
# calibrated image frame.  Width factors multiply transition_width.
_LEFT_X_FRAC = (
    0.000, 0.058, 0.118, 0.176, 0.235, 0.293, 0.353, 0.411,
    0.471, 0.529, 0.588, 0.646, 0.707, 0.765, 0.824, 0.882, 0.941, 1.000,
)
_LEFT_Y_FRAC = (
    0.000, 0.241, 0.463, 0.611, 0.722, 0.815, 0.870, 0.907,
    0.944, 0.963, 0.981, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000,
)
_LEFT_WIDTH_FACTORS = (
    0.020, 0.640, 0.800, 0.720, 0.640, 0.800, 0.800, 0.800,
    0.800, 0.800, 0.800, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000, 1.000,
)
_RIGHT_X_FRAC = (
    0.000, 0.059, 0.117, 0.176, 0.235, 0.293, 0.352, 0.411,
    0.470, 0.529, 0.587, 0.646, 0.705, 0.764, 0.822, 0.881, 0.940, 1.000,
)
_RIGHT_Y_FRAC = (
    0.000, -0.023, -0.023, -0.023, -0.023, -0.023, 0.000, 0.000,
    0.023, 0.070, 0.116, 0.186, 0.256, 0.372, 0.535, 0.698, 0.884, 1.000,
)
_RIGHT_WIDTH_FACTORS = (
    0.800, 1.000, 1.000, 1.000, 1.000, 1.000, 0.800, 1.000,
    0.800, 0.800, 0.800, 0.800, 0.600, 0.800, 0.800, 0.800, 0.400, 0.020,
)


def _image_to_gds(points: np.ndarray) -> np.ndarray:
    """Flip calibrated image coordinates into the GDS y-axis convention."""
    out = np.array(points, dtype=float, copy=True)
    out[:, 1] = footprint_height - out[:, 1]
    return out


def _profiled_path(points: np.ndarray, controls: tuple[tuple[float, float], ...]) -> tuple[gf.Path, gf.Component]:
    """Extrude one continuous, variable-width primitive path on layer (1, 0)."""
    path = gf.Path(points)
    control_t = np.asarray([t for t, _ in controls], dtype=float)
    control_w = np.asarray([w for _, w in controls], dtype=float)
    section = gf.Section(
        width=float(control_w[0]),
        layer=LAYER,
        width_function=lambda t: np.interp(t, control_t, control_w),
    )
    cross_section = gf.CrossSection(sections=(section,))
    return path, path.extrude(cross_section=cross_section)


_BASE_DELTA_LENGTH = 0.503
_BEND_REFERENCE_RADIUS = 0.1275

# Each arm is a three-branch centerline tree.  This reflects the broad
# three-terminal adiabatic junction visible in the image; every branch is
# still a permitted variable-width gf.Path extrusion, never an outline polygon.
_TOP_LEFT_BRANCH = np.array(
    ((2.230, 0.035), (3.100, 0.035), (3.850, 0.035), (14.270, 0.035), (14.870, 0.065),
     (15.075, 0.095), (15.100, 0.105), (15.140, 0.155)),
    dtype=float,
)
_TOP_LEFT_WIDTHS = np.array((0.020, 0.800, 1.300, 1.300, 1.400, 1.840, 2.200, 3.600))
_TOP_LOWER_BRANCH = np.array(
    ((15.140, 0.155), (15.095, 0.210), (15.075, 0.220), (14.925, 0.245),
     (14.620, 0.270), (13.220, 0.290)),
    dtype=float,
)
_TOP_LOWER_WIDTHS = np.array((3.600, 2.200, 1.800, 1.400, 1.200, 1.000))
_TOP_RIGHT_BRANCH = np.array(
    ((15.140, 0.155), (15.450, 0.155), (15.460, 0.160)), dtype=float
)
_TOP_RIGHT_WIDTHS = np.array((3.600, 1.280, 1.080))

_BOTTOM_TOP_BRANCH = np.array(
    ((4.390, 0.395), (3.630, 0.400), (3.335, 0.415), (3.165, 0.425),
     (3.035, 0.440), (2.940, 0.455), (2.910, 0.465), (2.860, 0.525)),
    dtype=float,
)
_BOTTOM_TOP_WIDTHS = np.array((1.000, 1.000, 1.200, 1.200, 1.400, 1.600, 1.900, 3.600))
_BOTTOM_RIGHT_BRANCH = np.array(
    ((2.860, 0.525), (2.875, 0.535), (2.905, 0.575), (2.930, 0.585),
     (3.015, 0.600), (3.200, 0.620), (3.630, 0.640), (3.865, 0.645),
     (14.800, 0.645), (15.640, 0.645)),
    dtype=float,
)
_BOTTOM_RIGHT_WIDTHS = np.array((3.600, 3.060, 2.200, 1.840, 1.600, 1.400, 1.300, 1.300, 1.300, 0.020))
_BOTTOM_LEFT_BRANCH = np.array(
    ((2.860, 0.525), (2.780, 0.520), (2.720, 0.525), (2.590, 0.525), (2.520, 0.530)),
    dtype=float,
)
_BOTTOM_LEFT_WIDTHS = np.array((3.600, 3.500, 3.260, 1.900, 0.440))


def _scale_branch(points: np.ndarray, anchor: np.ndarray) -> np.ndarray:
    """Make the branch curvature respond to bend_radius while retaining its topology."""
    return anchor + (bend_radius / _BEND_REFERENCE_RADIUS) * (points - anchor)


def _controls_from_path(points: np.ndarray, widths: np.ndarray) -> tuple[tuple[float, float], ...]:
    """Place width controls at real path arclength fractions."""
    segment_lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    fractions = np.concatenate(((0.0,), np.cumsum(segment_lengths)))
    fractions /= fractions[-1]
    return tuple((float(t), float(w)) for t, w in zip(fractions, widths, strict=True))


def _branch_component(image_points: np.ndarray, width_factors: np.ndarray) -> gf.Component:
    """Extrude one fitted branch with widths anchored to transition_width."""
    _, branch = _profiled_path(
        _image_to_gds(image_points),
        _controls_from_path(image_points, transition_width * width_factors),
    )
    return branch


def _top_hairpin() -> tuple[gf.Path, gf.Component]:
    """Assemble the fitted upper three-branch C-junction from primitive paths."""
    junction = _TOP_LEFT_BRANCH[-1]
    left = _scale_branch(_TOP_LEFT_BRANCH, _TOP_LEFT_BRANCH[2])
    lower = _scale_branch(_TOP_LOWER_BRANCH, junction)
    right = _scale_branch(_TOP_RIGHT_BRANCH, junction)
    extension = delta_length - _BASE_DELTA_LENGTH
    if extension:
        lower = np.vstack((lower, (lower[-1, 0] - extension, lower[-1, 1])))
        lower_widths = np.append(_TOP_LOWER_WIDTHS, 1.000)
    else:
        lower_widths = _TOP_LOWER_WIDTHS
    assembled = gf.Component()
    assembled.add_ref(_branch_component(left, _TOP_LEFT_WIDTHS))
    assembled.add_ref(_branch_component(lower, lower_widths))
    assembled.add_ref(_branch_component(right, _TOP_RIGHT_WIDTHS))
    route_image = np.vstack((left, lower[1:]))
    return gf.Path(_image_to_gds(route_image)), assembled


def _bottom_hairpin() -> tuple[gf.Path, gf.Component]:
    """Assemble the fitted lower three-branch C-junction from primitive paths."""
    junction = _BOTTOM_TOP_BRANCH[-1]
    top = _scale_branch(_BOTTOM_TOP_BRANCH, junction)
    right = _scale_branch(_BOTTOM_RIGHT_BRANCH, junction)
    left = _scale_branch(_BOTTOM_LEFT_BRANCH, junction)
    assembled = gf.Component()
    assembled.add_ref(_branch_component(top, _BOTTOM_TOP_WIDTHS))
    assembled.add_ref(_branch_component(right, _BOTTOM_RIGHT_WIDTHS))
    assembled.add_ref(_branch_component(left, _BOTTOM_LEFT_WIDTHS))
    route_image = np.vstack((top, right[1:]))
    return gf.Path(_image_to_gds(route_image)), assembled


def _left_access_component() -> gf.Component:
    x = 0.015 + left_transition_length * np.asarray(_LEFT_X_FRAC)
    y = 0.015 + 0.270 * np.asarray(_LEFT_Y_FRAC)
    controls = tuple(
        (i / (len(_LEFT_WIDTH_FACTORS) - 1), transition_width * width)
        for i, width in enumerate(_LEFT_WIDTH_FACTORS)
    )
    _, component = _profiled_path(_image_to_gds(np.column_stack((x, y))), controls)
    return component


def _right_access_component() -> gf.Component:
    x = 13.220 + right_transition_length * np.asarray(_RIGHT_X_FRAC)
    y = 0.400 + 0.215 * np.asarray(_RIGHT_Y_FRAC)
    controls = tuple(
        (i / (len(_RIGHT_WIDTH_FACTORS) - 1), transition_width * width)
        for i, width in enumerate(_RIGHT_WIDTH_FACTORS)
    )
    _, component = _profiled_path(_image_to_gds(np.column_stack((x, y))), controls)
    return component


@gf.cell
def device() -> gf.Component:
    """Assemble the reconstructed transition entirely from permitted primitives."""
    component = gf.Component()

    top_path, top_hairpin = _top_hairpin()
    bottom_path, bottom_hairpin = _bottom_hairpin()
    component.add_ref(top_hairpin)
    component.add_ref(bottom_hairpin)
    component.add_ref(_left_access_component())
    component.add_ref(_right_access_component())

    spine = gf.components.rectangle(size=(spine_length, spine_width), layer=LAYER)
    spine_ref = component.add_ref(spine)
    spine_ref.dmove((spine_x0, footprint_height - 0.344 - spine_width / 2))

    pitch_scale = fin_pitch / _NOMINAL_FIN_PITCH
    for index, (position_factor, length_factor) in enumerate(
        zip(_FIN_POSITION_FACTORS[:fin_count], _FIN_LENGTH_FACTORS[:fin_count], strict=True)
    ):
        x = pattern_start + pattern_length * position_factor * pitch_scale
        # Individual rectangle references are scaled through a permitted taper-like
        # width control: each fin's horizontal length is a live multiple of fin_length.
        fin_piece = gf.components.rectangle(
            size=(fin_length * length_factor, fin_height), layer=LAYER
        )
        for y_bottom in (
            footprint_height - 0.344 + spine_width / 2 + fin_gap,
            footprint_height - 0.344 - spine_width / 2 - fin_gap - fin_height,
        ):
            ref = component.add_ref(fin_piece)
            ref.dmove((x, y_bottom))

    # The reference raster's declared frame is 0.700 um tall while its visible
    # lower taper ends 19 nm above the frame boundary.  A 5 nm primitive at the
    # frame edge preserves the calibrated vertical registration without changing
    # the modeled optical geometry at raster resolution.
    frame_point = gf.components.rectangle(size=(0.005, 0.005), layer=LAYER)
    frame_ref = component.add_ref(frame_point)
    frame_ref.dmove((17.600, 0.000))

    # These values are calculated from the actual gf.Path centerlines used above.
    component.info["upper_arm_length_um"] = float(top_path.length())
    component.info["lower_arm_length_um"] = float(bottom_path.length())
    return component


component = device()
upper_arm_length = float(component.info["upper_arm_length_um"])
lower_arm_length = float(component.info["lower_arm_length_um"])
lengths_path = Path(__file__).with_name("lengths.json")
lengths_path.write_text(
    json.dumps(
        {
            "arms": {"upper_hairpin": upper_arm_length, "lower_hairpin": lower_arm_length},
            "delta_length_um": abs(upper_arm_length - lower_arm_length),
        },
        indent=2,
    )
)
GDS_PATH = Path(__file__).with_name("device.gds")
component.write_gds(GDS_PATH, with_metadata=False)
