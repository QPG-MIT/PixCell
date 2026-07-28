"""Primitives-only parametric recreation of the final7 nested-loop resonator."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import gdsfactory as gf


# Function-defining, JEE-substitutable geometry in microns.
layer = (1, 0)
outer_loop_width = 0.52
outer_loop_rx = 1.24
outer_loop_ry = 2.49
outer_loop_center_x = 1.50
outer_loop_center_y = 2.75
outer_loop_superellipse_power = 4.0

inner_loop_width = 0.36
inner_loop_left_x = 0.34
inner_loop_right_x = 2.66
inner_loop_top_attach_y = 1.620
inner_loop_bottom_attach_y = 3.880
inner_loop_outer_corner_x = 0.72
inner_loop_inner_corner_x = 0.49
inner_loop_inner_corner_y = 2.10
inner_loop_center_half_height = 0.36

aperture_block_x = 1.054
aperture_block_width = 0.886
aperture_block_height = 1.030
top_aperture_block_y = 1.318
bottom_aperture_block_y = 3.159
aperture_margin_x = 0.059
aperture_margin_y = 0.247
aperture_width = 0.330
aperture_height = 0.560
aperture_gap = 0.110
phase_trim_width = 0.200
phase_trim_y = 2.235
delta_length = 0.0


@gf.cell
def superelliptical_outer_loop() -> gf.Component:
    """Closed oval waveguide made by extruding a GF Path, not a polygon."""
    theta = np.linspace(0.0, 2.0 * np.pi, 721)
    exponent = 2.0 / outer_loop_superellipse_power
    points = np.column_stack(
        (
            outer_loop_center_x
            + outer_loop_rx * np.sign(np.cos(theta)) * np.abs(np.cos(theta)) ** exponent,
            outer_loop_center_y
            + outer_loop_ry * np.sign(np.sin(theta)) * np.abs(np.sin(theta)) ** exponent,
        )
    )
    path = gf.Path(points)
    return path.extrude(width=outer_loop_width, layer=layer, simplify=0.001)


@gf.cell
def inner_loop_side_connectors() -> gf.Component:
    """Two faceted paths joining the aperture blocks into the inner loop."""
    left_points = [
        (aperture_block_x, inner_loop_top_attach_y),
        (inner_loop_outer_corner_x, inner_loop_top_attach_y),
        (inner_loop_inner_corner_x, inner_loop_inner_corner_y),
        (inner_loop_left_x, outer_loop_center_y - inner_loop_center_half_height),
        (inner_loop_left_x, outer_loop_center_y + inner_loop_center_half_height),
        (inner_loop_inner_corner_x, 5.50 - inner_loop_inner_corner_y),
        (inner_loop_outer_corner_x, inner_loop_bottom_attach_y),
        (aperture_block_x, inner_loop_bottom_attach_y),
    ]
    right_points = [
        (2.0 * outer_loop_center_x - x, y) for x, y in left_points
    ]
    component = gf.Component()
    component.add_ref(gf.Path(left_points).extrude(width=inner_loop_width, layer=layer))
    component.add_ref(gf.Path(right_points).extrude(width=inner_loop_width, layer=layer))
    return component


@gf.cell
def double_aperture(y0: float) -> gf.Component:
    """A rectangular double-aperture loading section, formed with booleans."""
    block = gf.components.rectangle(
        size=(aperture_block_width, aperture_block_height), layer=layer
    )
    holes = gf.Component()
    left_hole = holes.add_ref(
        gf.components.rectangle(size=(aperture_width, aperture_height), layer=layer)
    )
    left_hole.dmove((aperture_margin_x, aperture_margin_y))
    right_hole = holes.add_ref(
        gf.components.rectangle(size=(aperture_width, aperture_height), layer=layer)
    )
    right_hole.dmove((aperture_margin_x + aperture_width + aperture_gap, aperture_margin_y))
    apertured = gf.boolean(block, holes, operation="not", layer=layer)
    component = gf.Component()
    ref = component.add_ref(apertured)
    ref.dmove((aperture_block_x, y0))
    return component


def phase_trim_paths() -> tuple[gf.Path, gf.Path]:
    """Reference and tunable paths for the upper phase-trim rail."""
    reference = gf.Path(
        [(aperture_block_x, phase_trim_y), (aperture_block_x + aperture_block_width, phase_trim_y)]
    )
    trim = gf.Path(
        [
            (aperture_block_x, phase_trim_y),
            (aperture_block_x + aperture_block_width + delta_length, phase_trim_y),
        ]
    )
    return reference, trim


@gf.cell
def phase_trim() -> gf.Component:
    """A live path-length trim integrated with the upper aperture rail."""
    _, trim = phase_trim_paths()
    return trim.extrude(width=phase_trim_width, layer=layer)


@gf.cell
def device() -> gf.Component:
    """Nested oval resonator with mirrored double-aperture coupling regions."""
    component = gf.Component()
    component.add_ref(superelliptical_outer_loop())
    component.add_ref(inner_loop_side_connectors())
    component.add_ref(double_aperture(top_aperture_block_y))
    component.add_ref(double_aperture(bottom_aperture_block_y))
    component.add_ref(phase_trim())
    return component


if __name__ == "__main__":
    reference_path, trim_path = phase_trim_paths()
    lengths = {
        "arms": {
            "reference_um": reference_path.length(),
            "trimmed_um": trim_path.length(),
        },
        "delta_length_um": abs(trim_path.length() - reference_path.length()),
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(lengths, indent=2))
    device().write_gds(Path(__file__).with_name("device.gds"), with_metadata=False)
