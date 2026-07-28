"""Primitives-only parametric recreation of the final8 multi-rail device."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Function-defining top-level tunables (all dimensions are in micrometers).
overall_length = 120.0
transfer_length = 98.0
delta_length = 0.0
taper_length = 11.0
tip_width = 1.40
rail_width = 0.068
rail_gap = 0.032
rail_count = 5
slab_width = 0.470
rail_group_center_offset = 1.000
center_rail_pitch = 0.100
compound_gap = 0.031
outer_stem_x = 4.85
inner_stem_x = 7.10
transition_branch_x = 9.60
layer = (1, 0)


def _line_path(x0: float, x1: float, y: float) -> gf.Path:
    """Straight centerline with explicit absolute coordinates."""
    return gf.Path(np.array([[x0, y], [x1, y]], dtype=float))


def _cubic_path(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    samples: int = 101,
) -> gf.Path:
    """Cubic-Bezier centerline represented as a legal gf.Path primitive."""
    t = np.linspace(0.0, 1.0, samples)
    omt = 1.0 - t
    points = (
        omt[:, None] ** 3 * np.asarray(p0)
        + 3.0 * omt[:, None] ** 2 * t[:, None] * np.asarray(p1)
        + 3.0 * omt[:, None] * t[:, None] ** 2 * np.asarray(p2)
        + t[:, None] ** 3 * np.asarray(p3)
    )
    return gf.Path(points)


def _add_constant_path(component: gf.Component, path: gf.Path, width: float) -> None:
    primitive = gf.path.extrude(path, layer=layer, width=width)
    component.add_ref(primitive)


def _add_width_transition(
    component: gf.Component,
    path: gf.Path,
    width1: float,
    width2: float,
) -> None:
    xs1 = gf.CrossSection(
        sections=(gf.Section(width=width1, layer=layer, name="core"),)
    )
    xs2 = gf.CrossSection(
        sections=(gf.Section(width=width2, layer=layer, name="core"),)
    )
    transition = gf.path.transition(xs1, xs2, width_type="sine")
    primitive = gf.path.extrude_transition(path, transition)
    component.add_ref(primitive)


def _add_compound_half(component: gf.Component, sign: float) -> None:
    """Add one mirrored slab + five-rail adiabatic compound section."""
    x0 = taper_length
    x1 = taper_length + transfer_length
    pitch = rail_width + rail_gap
    group_to_slab = (
        (rail_count - 1) / 2.0 * pitch
        + rail_width / 2.0
        + compound_gap
        + slab_width / 2.0
    )
    slab_y = sign * (rail_group_center_offset - group_to_slab)

    slab_path = _line_path(x0, x1, slab_y)
    _add_constant_path(component, slab_path, slab_width)

    left_slab_turn = _cubic_path(
        (outer_stem_x, sign * 2.0),
        (outer_stem_x, sign * 0.78),
        (x0 - 3.2, slab_y),
        (x0, slab_y),
    )
    right_slab_turn = _cubic_path(
        (x1, slab_y),
        (x1 + 3.2, slab_y),
        (overall_length - outer_stem_x, sign * 0.78),
        (overall_length - outer_stem_x, sign * 2.0),
    )
    _add_width_transition(component, left_slab_turn, tip_width, slab_width)
    _add_width_transition(component, right_slab_turn, slab_width, tip_width)

    rail_ys = [
        sign * (rail_group_center_offset + (index - (rail_count - 1) / 2.0) * pitch)
        for index in range(rail_count)
    ]
    for rail_y in rail_ys:
        _add_constant_path(component, _line_path(x0, x1, rail_y), rail_width)

        left_branch = _cubic_path(
            (inner_stem_x, sign * 2.0),
            (inner_stem_x, sign * 1.38),
            (transition_branch_x, rail_y),
            (x0, rail_y),
        )
        right_branch = _cubic_path(
            (x1, rail_y),
            (overall_length - transition_branch_x, rail_y),
            (overall_length - inner_stem_x, sign * 1.38),
            (overall_length - inner_stem_x, sign * 2.0),
        )
        _add_constant_path(component, left_branch, rail_width)
        _add_constant_path(component, right_branch, rail_width)

    # The wide vertical entry/exit stems are primitive paths.  The five
    # branches overlap these stems and fan out smoothly into separate rails.
    left_stem = gf.Path(
        np.array(
            [
                [inner_stem_x, sign * 2.0],
                [inner_stem_x, sign * 1.62],
            ],
            dtype=float,
        )
    )
    right_stem = gf.Path(
        np.array(
            [
                [overall_length - inner_stem_x, sign * 1.62],
                [overall_length - inner_stem_x, sign * 2.0],
            ],
            dtype=float,
        )
    )
    _add_width_transition(component, left_stem, tip_width, 0.56)
    _add_width_transition(component, right_stem, 0.56, tip_width)


@gf.cell
def multi_rail_device() -> gf.Component:
    component = gf.Component()

    pitch = center_rail_pitch
    center_ys = [(index - (rail_count - 1) / 2.0) * pitch for index in range(rail_count)]

    arm_a = _line_path(0.0, overall_length + delta_length, center_ys[0])
    arm_b = _line_path(0.0, overall_length, center_ys[-1])
    _add_constant_path(component, arm_a, rail_width)
    _add_constant_path(component, arm_b, rail_width)

    for rail_y in center_ys[1:-1]:
        _add_constant_path(
            component,
            _line_path(0.0, overall_length, rail_y),
            rail_width,
        )

    _add_compound_half(component, sign=1.0)
    _add_compound_half(component, sign=-1.0)

    component.info["arm_a_length_um"] = float(arm_a.length())
    component.info["arm_b_length_um"] = float(arm_b.length())
    return component


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    device = multi_rail_device()
    # Metadata is disabled so the physical device remains the unambiguous
    # GDS top cell for deterministic hierarchy-aware area measurement.
    device.write_gds(output_dir / "device.gds", with_metadata=False)

    arm_a_length = float(device.info["arm_a_length_um"])
    arm_b_length = float(device.info["arm_b_length_um"])
    lengths = {
        "arms": {
            "rail_a": arm_a_length,
            "rail_b": arm_b_length,
        },
        "delta_length_um": abs(arm_a_length - arm_b_length),
        "coupler": {
            "length_um": transfer_length,
            "gap_um": rail_gap,
            "width_um": rail_width,
        },
    }
    (output_dir / "lengths.json").write_text(json.dumps(lengths, indent=2) + "\n")
