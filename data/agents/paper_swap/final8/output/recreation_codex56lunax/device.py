"""Primitive-only recreation of the final8 paper-swap mask.

The drawing is a vertically mirrored ladder of narrow horizontal guides,
bounded by wide curved/sloped side rails and broad end bodies. All dimensions
are module-level numeric tunables for HOMI/JEE.
"""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


# Function-defining tunables (microns).
footprint_length = 120.0
bar_length = 120.0
reference_length = 120.0
bar_width = 0.068
bar_pitch = 0.100
rung_pitch = 0.100
rung_start = 0.764
rail_width = 1.38
outer_rail_width = 1.42
outer_body_height = 0.470
outer_body_width = 106.0
outer_body_width_bottom = 99.5
outer_body_top = 1.264
outer_rail_top_center = 4.85
outer_rail_bottom_center = 8.10
inner_rail_top_center = 7.09
inner_rail_bottom_center = 9.60
end_margin = 7.75
rung_left = end_margin
rung_length = 104.5
central_start = 1.806
layer = (1, 0)
footprint_height = 4.0


def _image_rect(parent: gf.Component, x: float, y_top: float, length: float, height: float) -> None:
    """Add a rectangle specified in image coordinates (origin is upper-left)."""
    rect = gf.components.rectangle(size=(length, height), layer=layer)
    ref = parent.add_ref(rect)
    ref.move((x, footprint_height - y_top - height))


def _image_curve_path(
    x_top: float,
    x_bottom: float,
    y_top: float,
    y_bottom: float,
    width: float,
) -> gf.Component:
    """Extrude a gently bowed rail from image-space endpoints."""
    points = []
    count = 20
    for i in range(count + 1):
        t = i / count
        x = x_top + (x_bottom - x_top) * (t**1.65)
        y_image = y_top + (y_bottom - y_top) * t
        points.append((x, footprint_height - y_image))
    return gf.Path(points).extrude(layer=layer, width=width)


def _top_end() -> gf.Component:
    top = gf.Component("top_end")

    # Broad U-like end body. The short primitive bands approximate the smooth
    # sidewall turn while keeping the calibrated bbox exactly at the footprint.
    outer_left_profile = (
        (0.000, 0.200, outer_rail_top_center - outer_rail_width / 2, outer_rail_width),
        (0.200, 0.450, 4.50, 1.50),
        (0.450, 0.700, 5.10, 1.65),
        (0.700, 0.900, 5.60, 1.75),
        (0.900, 1.100, 6.20, 2.20),
        (1.100, outer_body_top, outer_rail_bottom_center - 2.70 / 2, 2.70),
    )
    for y0, y1, x0, width in outer_left_profile:
        _image_rect(top, x0, y0, width, y1 - y0)
        _image_rect(top, footprint_length - x0 - width, y0, width, y1 - y0)
    body = gf.components.taper(
        length=outer_body_height,
        width1=outer_body_width_bottom,
        width2=outer_body_width,
        layer=layer,
        with_two_ports=False,
    )
    body_ref = top.add_ref(body)
    body_ref.rotate(90)
    body_ref.move((60.0, footprint_height - outer_body_top - outer_body_height))

    # Five narrow rungs joined by the two broad inner rails.
    inner_left_profile = (
        (0.000, 0.200, inner_rail_top_center - rail_width / 2, rail_width),
        (0.200, 0.450, 6.74, 1.50),
        (0.450, 0.700, 7.30, 1.65),
        (0.700, 0.900, 7.80, 2.10),
        (0.900, 1.100, 8.50, 1.60),
        (1.100, 1.235, inner_rail_bottom_center - 1.40 / 2, 1.40),
    )
    for y0, y1, x0, width in inner_left_profile:
        _image_rect(top, x0, y0, width, y1 - y0)
        _image_rect(top, footprint_length - x0 - width, y0, width, y1 - y0)
    for index in range(5):
        _image_rect(top, rung_left, rung_start + index * rung_pitch, rung_length, bar_width)

    return top


@gf.cell
def device() -> gf.Component:
    component = gf.Component("final8_recreation")

    # End structures are mirror images about the physical y=2 um centerline.
    top = _top_end()
    component.add_ref(top)
    bottom = component.add_ref(top)
    bottom.dmirror_y(y=2.0)

    # Five full-length center guides. The first is the live parametric arm
    # used by the local knob-response proof; the other four are fixed peers.
    active_center = central_start
    active_path = gf.path.straight(bar_length)
    active_path.move((0, footprint_height - active_center))
    component.add_ref(active_path.extrude(layer=layer, width=bar_width))
    for index in range(1, 5):
        center = central_start + index * bar_pitch
        path = gf.path.straight(reference_length)
        path.move((0, footprint_height - center))
        component.add_ref(path.extrude(layer=layer, width=bar_width))

    reference_path = gf.path.straight(reference_length)
    delta_length_um = abs(active_path.length() - reference_path.length())
    payload = {
        "arms": {"active": float(active_path.length()), "reference": float(reference_path.length())},
        "delta_length_um": float(delta_length_um),
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(payload, indent=2))
    return component


if __name__ == "__main__":
    device().write_gds("device.gds", with_metadata=False)
