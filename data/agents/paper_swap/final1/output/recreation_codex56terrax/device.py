"""Primitives-only Phase-A recreation of a symmetric adiabatic 1x2 coupler."""

from math import pow
from pathlib import Path

import gdsfactory as gf


# Live parametric contract: all geometry-driving dimensions are top-level values in um.
layer = (1, 0)
total_length = 40.0
input_width = 0.268
input_straight_length = 3.05
input_taper_length = 22.00
input_tip_width = 0.070
input_center_offset = 0.016
rail_start_x = 3.05
rail_start_width = 0.070
rail_width = 0.242
rail_taper_length = 22.00
upper_rail_start_offset = 0.282
lower_rail_start_offset = -0.262
s_bend_straight_length = 0.45
s_bend_length = 10.65
upper_output_offset = 0.730
lower_output_offset = -0.728
s_bend_points = 81


def smootherstep(t: float) -> float:
    """Zero-slope quintic interpolation for the two adiabatic output S-bends."""
    return 6.0 * pow(t, 5) - 15.0 * pow(t, 4) + 10.0 * pow(t, 3)


def rail_path(start_y: float, end_y: float) -> gf.Path:
    """Return one rail's smooth S-bend and its straight output extension."""
    x0 = rail_start_x + rail_taper_length
    bend_start = x0 + s_bend_straight_length
    points = [(x0, start_y), (bend_start, start_y)]
    for index in range(s_bend_points):
        t = index / (s_bend_points - 1)
        points.append((bend_start + s_bend_length * t, start_y + (end_y - start_y) * smootherstep(t)))
    points.append((total_length, end_y))
    return gf.Path(points)


@gf.cell
def adiabatic_splitter() -> gf.Component:
    """Central taper plus two widening rails and opposite smooth S-bend outputs."""
    component = gf.Component()

    input_straight = component.add_ref(
        gf.components.straight(
            length=input_straight_length,
            cross_section=gf.cross_section.cross_section(width=input_width, layer=layer),
        )
    )
    input_straight.dmove((0, input_center_offset))

    input_taper = component.add_ref(
        gf.components.taper(
            length=input_taper_length,
            width1=input_width,
            width2=input_tip_width,
            layer=layer,
        )
    )
    input_taper.dmove((input_straight_length, input_center_offset))

    for start_y, end_y in (
        (upper_rail_start_offset, upper_output_offset),
        (lower_rail_start_offset, lower_output_offset),
    ):
        rail_taper = component.add_ref(
            gf.components.taper(
                length=rail_taper_length,
                width1=rail_start_width,
                width2=rail_width,
                layer=layer,
            )
        )
        rail_taper.dmove((rail_start_x, start_y))
        component.add_ref(rail_path(start_y, end_y).extrude(width=rail_width, layer=layer))

    return component


OUTPUT_GDS = Path(__file__).with_name("device.gds")
component = adiabatic_splitter()
component.write_gds(OUTPUT_GDS)
