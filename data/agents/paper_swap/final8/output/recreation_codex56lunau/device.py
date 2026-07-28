"""Primitive-only recreation of the final8 paper-swap device image.

The target is a symmetric five-rail folded/fanout structure. All dimensions
that define the visible geometry are top-level assignments so the conductor
can audit and retune them without changing the assembly logic.
"""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Parametric contract: visible/function-defining dimensions are top-level.
guide_width_um = 0.068
rail_pitch_um = 0.100
rail_count = 5
footprint_width_um = 4.0
rail_length_um = 120.0
arm_extension_um = 0.0
central_first_y_um = 2.19475
central_pitch_um = 0.10075
body_length_um = 106.20
body_bottom_width_um = 100.00
body_height_um = 0.471
body_bottom_y_um = 2.2667
fanout_first_y_um = 3.2020
fanout_base_left_um = 7.76
fanout_inset_per_rail_um = 0.33
side_lead_width_um = 1.50
outer_lead_mid_width_um = 2.20
outer_lead_junction_width_um = 3.25
inner_lead_bottom_width_um = 2.30
outer_lead_top_x_um = 4.83
outer_lead_bottom_x_um = 8.45
inner_lead_top_x_um = 7.08
inner_lead_bottom_x_um = 8.55
halfline_y_um = 2.0


def _add_rectangle(component: gf.Component, x: float, y: float, width: float, height: float) -> None:
    ref = component << gf.components.rectangle(size=(width, height), layer=LAYER)
    ref.dmove((x, y))


def _add_path(component: gf.Component, points: list[tuple[float, float]], width: float) -> gf.Path:
    path = gf.Path(points)
    shape = path.extrude(cross_section=gf.cross_section.strip(width=width, layer=LAYER))
    component.add_ref(shape)
    return path


def _add_vertical_taper(
    component: gf.Component,
    y0: float,
    y1: float,
    center_x: float,
    width0: float,
    width1: float,
) -> None:
    """Add a linear cross-section taper along +y using the primitive taper."""
    taper = gf.components.taper(
        length=y1 - y0,
        width1=width0,
        width2=width1,
        layer=LAYER,
        with_bbox=False,
    )
    ref = component << taper
    ref.rotate(90)
    ref.dmove((center_x, y0))


@gf.cell
def top_half() -> gf.Component:
    """Build the upper half; the lower half is a reflection about y=2 um."""
    c = gf.Component()

    # The broad outer body is a primitive linear taper in the vertical axis.
    _add_vertical_taper(
        c,
        body_bottom_y_um,
        body_bottom_y_um + body_height_um,
        rail_length_um / 2,
        body_bottom_width_um,
        body_length_um,
    )

    # Outer leads are broad, vertically oriented tapers. Three overlapping
    # segments approximate the measured inward bow while keeping the endpoint
    # at the 4 um footprint edge exact.
    _add_vertical_taper(c, 3.50, footprint_width_um, 4.85, 1.65, side_lead_width_um)
    _add_vertical_taper(c, 2.90, 3.50, 6.30, outer_lead_mid_width_um, 1.65)
    _add_vertical_taper(c, 2.737, 2.90, outer_lead_bottom_x_um, outer_lead_junction_width_um, outer_lead_mid_width_um)
    _add_vertical_taper(c, 3.50, footprint_width_um, rail_length_um - 4.85, 1.65, side_lead_width_um)
    _add_vertical_taper(c, 2.90, 3.50, rail_length_um - 6.30, outer_lead_mid_width_um, 1.65)
    _add_vertical_taper(c, 2.737, 2.90, rail_length_um - outer_lead_bottom_x_um, outer_lead_junction_width_um, outer_lead_mid_width_um)

    # Five narrow inner rails fan out toward the two side leads.
    for index in range(rail_count):
        y = fanout_first_y_um - index * rail_pitch_um
        x_left = fanout_base_left_um + index * fanout_inset_per_rail_um
        x_right = rail_length_um - x_left
        _add_path(c, [(x_left, y), (x_right, y)], guide_width_um)

    # Small primitive centerline links represent the alternating folded turns
    # between neighboring fanout rails.
    for index in range(rail_count - 1):
        y0 = fanout_first_y_um - index * rail_pitch_um
        y1 = fanout_first_y_um - (index + 1) * rail_pitch_um
        x0 = fanout_base_left_um + index * fanout_inset_per_rail_um
        x1 = fanout_base_left_um + (index + 1) * fanout_inset_per_rail_um
        if index % 2 == 0:
            points = [(rail_length_um - x0, y0), (rail_length_um - x1, y1)]
        else:
            points = [(x0, y0), (x1, y1)]
        _add_path(c, points, guide_width_um)

    # Inner leads likewise widen and shift inward toward the five rail ends.
    _add_vertical_taper(c, 3.70, footprint_width_um, inner_lead_top_x_um, 1.60, side_lead_width_um)
    _add_vertical_taper(c, 3.45, 3.70, 7.95, 1.75, 1.60)
    _add_vertical_taper(c, 3.237, 3.45, 8.85, inner_lead_bottom_width_um, 1.75)
    _add_vertical_taper(c, 3.70, footprint_width_um, rail_length_um - inner_lead_top_x_um, 1.60, side_lead_width_um)
    _add_vertical_taper(c, 3.45, 3.70, rail_length_um - 7.95, 1.75, 1.60)
    _add_vertical_taper(c, 3.237, 3.45, rail_length_um - 8.85, inner_lead_bottom_width_um, 1.75)

    return c


@gf.cell
def build_device() -> gf.Component:
    """Assemble the mirrored halves and the five central rails."""
    c = gf.Component()

    c << top_half()
    lower = c << top_half()
    lower.drotate(180, center=(rail_length_um / 2, halfline_y_um))

    # Two paths are the measured arms for the local knob-response contract.
    # Only the upper primary arm responds to arm_extension_um.
    arm_a_y = central_first_y_um
    arm_b_y = central_first_y_um - 4 * central_pitch_um
    arm_a = _add_path(c, [(0.0, arm_a_y), (rail_length_um + arm_extension_um, arm_a_y)], guide_width_um)
    arm_b = _add_path(c, [(0.0, arm_b_y), (rail_length_um, arm_b_y)], guide_width_um)
    for index in range(1, rail_count - 1):
        y = central_first_y_um - index * central_pitch_um
        _add_path(c, [(0.0, y), (rail_length_um, y)], guide_width_um)

    arms = {"upper_primary": float(arm_a.length()), "lower_reference": float(arm_b.length())}
    delta_length_um = abs(arms["upper_primary"] - arms["lower_reference"])
    Path(__file__).with_name("lengths.json").write_text(
        json.dumps({"arms": arms, "delta_length_um": delta_length_um}, indent=2)
    )
    return c


if __name__ == "__main__":
    device = build_device()
    device = device.copy()
    device.flatten(merge=False)
    device.write_gds("device.gds")
