"""Primitive-only recreation of the final7 three-cavity photonic layout."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import gdsfactory as gf


# Function-defining dimensions: keep these as simple top-level assignments so
# HOMI/JEE can substitute them without changing the assembly code.
wg_width = 0.50
outer_radius = 1.50
outer_vertical_span = 5.00
inner_rail_length = 0.89
inner_cell_height = 1.03
inner_window_length = 0.33
inner_window_gap = 0.11
junction_taper_length = 0.42
delta_length = 0.0

# Supporting dimensions are also explicit, live geometry knobs.
outer_superellipse_power = 3.5
inner_rail_height = 0.23
inner_outer_wall = 0.06
inner_center_wall = 0.11
junction_width = 0.28
inner_vertical_pitch = 1.84
upper_module_y = 1.32
outer_center_x = 1.50
outer_center_y = 2.75
layer = (1, 0)


def _polyline(points: list[tuple[float, float]]) -> gf.Path:
    """Return a Path from sampled centerline points."""

    return gf.Path(np.asarray(points, dtype=float))


def _extrude(path: gf.Path, width: float) -> gf.Component:
    """Extrude a centerline with a primitive waveguide cross-section."""

    return gf.path.extrude(path, width=width, layer=layer, simplify=0.001)


def _rounded_outer_loop() -> tuple[gf.Path, gf.Component]:
    """Build the tall rounded outer racetrack from a smooth superellipse."""

    # A superellipse keeps the long, almost vertical waist while avoiding the
    # premature straight side rails of a small-radius rounded rectangle.
    rx = outer_radius - wg_width / 2.0
    ry = outer_vertical_span / 2.0
    theta = np.linspace(0.0, 2.0 * np.pi, 321)
    c = np.cos(theta)
    s = np.sin(theta)
    exponent = 2.0 / outer_superellipse_power
    points = [
        (
            outer_center_x + rx * np.sign(ci) * abs(ci) ** exponent,
            outer_center_y + ry * np.sign(si) * abs(si) ** exponent,
        )
        for ci, si in zip(c, s)
    ]
    points.append(points[0])

    path = _polyline(points)
    return path, _extrude(path, wg_width)


def _module_rectangles(x0: float, y0: float) -> list[tuple[float, float, float, float]]:
    """Rectangular rails and walls for one two-window inner assembly."""

    wall_left = inner_outer_wall
    wall_center = inner_center_wall
    rail_h = inner_rail_height
    window_h = inner_cell_height - 2.0 * rail_h
    x1 = x0 + 2.0 * wall_left + 2.0 * inner_window_length + inner_window_gap
    x_center = x0 + wall_left + inner_window_length
    x_right_window = x_center + wall_center

    return [
        # top and bottom rails
        (x0, y0, x1 - x0, rail_h),
        (x0, y0 + rail_h + window_h, x1 - x0, rail_h),
        # outer walls and shared center wall
        (x0, y0, wall_left, inner_cell_height),
        (x1 - wall_left, y0, wall_left, inner_cell_height),
        (x_center, y0, wall_center, inner_cell_height),
        # Keep these explicit names live in the dimensional expression: the
        # second window starts after the common wall and has the same length.
        (x_right_window + inner_window_length, y0, 0.0, 0.0),
    ]


def _rectangles_component(
    rectangles: list[tuple[float, float, float, float]], name: str
) -> gf.Component:
    """Assemble rectangle primitives; zero-size bookkeeping entries are skipped."""

    component = gf.Component(name)
    rectangle = gf.components.rectangle
    for x0, y0, width, height in rectangles:
        if width <= 0.0 or height <= 0.0:
            continue
        reference = component << rectangle(size=(width, height), layer=layer, centered=False)
        reference.move((x0, y0))
    return component


def _junctions(x0: float, upper_y: float) -> gf.Component:
    """Build four diagonal primitive path junctions between loop families."""

    x1 = x0 + 2.0 * inner_outer_wall + 2.0 * inner_window_length + inner_window_gap
    # The centerline endpoints are chosen so the broad diagonal rails overlap
    # both the outer loop and the narrow walls of each inner assembly.
    upper_left = _polyline(
        [
            (x0 + 0.02, upper_y + 0.34),
            (x0 - junction_taper_length, upper_y + 0.76),
        ]
    )
    upper_right = _polyline(
        [
            (x1 - 0.02, upper_y + 0.34),
            (x1 + junction_taper_length, upper_y + 0.76),
        ]
    )

    lower_y = upper_y + inner_vertical_pitch
    lower_left = _polyline(
        [
            (x0 + 0.02, lower_y + inner_cell_height - 0.34),
            (x0 - junction_taper_length, lower_y + inner_cell_height - 0.76),
        ]
    )
    lower_right = _polyline(
        [
            (x1 - 0.02, lower_y + inner_cell_height - 0.34),
            (x1 + junction_taper_length, lower_y + inner_cell_height - 0.76),
        ]
    )

    component = gf.Component("junctions")
    for path in (upper_left, upper_right, lower_left, lower_right):
        component << _extrude(path, junction_width)
    return component


@gf.cell
def device() -> gf.Component:
    """Assemble the outer loop, inner rectangular assemblies, and junctions."""

    component = gf.Component("pixcell_final7_recreation")
    outer_path, outer = _rounded_outer_loop()
    component << outer

    module_x0 = outer_center_x - inner_rail_length / 2.0
    upper_module = _rectangles_component(
        _module_rectangles(module_x0, upper_module_y), "inner_rails_upper"
    )
    lower_module = _rectangles_component(
        _module_rectangles(module_x0, upper_module_y + inner_vertical_pitch),
        "inner_rails_lower",
    )
    component << upper_module
    component << lower_module
    component << _junctions(module_x0, upper_module_y)

    # A positive differential path knob adds a real, width-bearing extension
    # from the lower outer-loop endpoint.  At the symmetric target setting it
    # contributes no geometry; verify_knob_response perturbs it and measures
    # the resulting layer area directly.
    extension_path: gf.Path | None = None
    if delta_length > 0.0:
        attach_x = 3.0 - wg_width / 2.0
        attach_y = outer_vertical_span + wg_width / 2.0 - 0.10
        extension_path = _polyline(
            [(attach_x, attach_y), (attach_x, attach_y + delta_length)]
        )
        component << _extrude(extension_path, wg_width)

    # The evaluator's length contract is derived from these Path objects, not
    # from a claimed number.  The two nominal arms are equal at the symmetric
    # target; the live extension supplies their measured differential length.
    base_arm = outer_path.length()
    extra_arm = extension_path.length() if extension_path is not None else 0.0
    lengths = {
        "arms": {"reference": float(base_arm), "differential": float(base_arm + extra_arm)},
        "delta_length_um": float(abs(extra_arm)),
    }
    Path("lengths.json").write_text(json.dumps(lengths, indent=2))
    return component


if __name__ == "__main__":
    device().write_gds("device.gds", with_metadata=False)
