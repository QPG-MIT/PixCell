from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


layer = (1, 0)

# Footprint anchors for the absolute rasterizer.
footprint_length_um = 25.0
footprint_width_um = 10.0
anchor_size_um = 0.01

# Multimode/slab body.
body_x0_um = 2.78
body_y0_um = 2.70
body_length_um = 19.43
body_width_um = 3.70

# Top access ports.
guide_width_um = 1.22
top_y_um = 9.14
top_straight_length_um = 1.34
top_taper_length_um = 1.40
top_taper_wide_um = 2.18
top_port1_x_um = 5.45
top_port2_x_um = 9.63
top_port3_x_um = 15.04
top_port4_x_um = 19.50

# Bottom access port.
bottom_center_x_um = 12.49
bottom_guide_width_um = 1.16
bottom_taper_wide_um = 2.27
bottom_taper_length_um = 0.85
delta_length = 0.12


def _add_rect(
    c: gf.Component,
    *,
    x0: float,
    y0: float,
    width: float,
    height: float,
) -> None:
    ref = c << gf.components.rectangle(
        size=(width, height),
        layer=layer,
        centered=False,
        port_type=None,
    )
    ref.dmove((x0, y0))


def _add_vertical_taper(
    c: gf.Component,
    *,
    center_x: float,
    y_narrow: float,
    length: float,
    width_narrow: float,
    width_wide: float,
    points_down: bool,
) -> None:
    taper = gf.components.taper(
        length=length,
        width1=width_narrow,
        width2=width_wide,
        layer=layer,
        with_two_ports=False,
        with_bbox=False,
    )
    ref = c << taper
    if points_down:
        ref.drotate(-90)
        ref.dmove((center_x, y_narrow))
    else:
        ref.drotate(90)
        ref.dmove((center_x, y_narrow))


@gf.cell
def build_device() -> gf.Component:
    c = gf.Component()

    body_top = body_y0_um + body_width_um
    body_x1 = body_x0_um + body_length_um

    # Tiny material anchors preserve the specified footprint for absolute
    # rasterization while contributing negligible area.
    _add_rect(c, x0=0.0, y0=0.0, width=anchor_size_um, height=anchor_size_um)
    _add_rect(
        c,
        x0=footprint_length_um - anchor_size_um,
        y0=footprint_width_um - anchor_size_um,
        width=anchor_size_um,
        height=anchor_size_um,
    )

    _add_rect(
        c,
        x0=body_x0_um,
        y0=body_y0_um,
        width=body_length_um,
        height=body_width_um,
    )

    top_centers = (
        top_port1_x_um,
        top_port2_x_um,
        top_port3_x_um,
        top_port4_x_um,
    )
    top_taper_top = body_top + top_taper_length_um
    for center_x in top_centers:
        _add_vertical_taper(
            c,
            center_x=center_x,
            y_narrow=top_taper_top,
            length=top_taper_length_um,
            width_narrow=guide_width_um,
            width_wide=top_taper_wide_um,
            points_down=True,
        )
        _add_rect(
            c,
            x0=center_x - guide_width_um / 2,
            y0=top_taper_top,
            width=guide_width_um,
            height=top_straight_length_um,
        )

    bottom_taper_narrow_y = body_y0_um - bottom_taper_length_um
    _add_vertical_taper(
        c,
        center_x=bottom_center_x_um,
        y_narrow=bottom_taper_narrow_y,
        length=bottom_taper_length_um,
        width_narrow=bottom_guide_width_um,
        width_wide=bottom_taper_wide_um,
        points_down=False,
    )
    _add_rect(
        c,
        x0=bottom_center_x_um - bottom_guide_width_um / 2,
        y0=bottom_taper_narrow_y - delta_length,
        width=bottom_guide_width_um,
        height=delta_length,
    )

    # Ensure these names are kept live and make the bbox intent explicit.
    _ = body_x1
    return c


def write_lengths_json(path: Path) -> None:
    reference_path = gf.Path(
        [
            (bottom_center_x_um, body_y0_um),
            (bottom_center_x_um, body_y0_um - bottom_taper_length_um),
        ]
    )
    lower_access_path = gf.Path(
        [
            (bottom_center_x_um, body_y0_um),
            (bottom_center_x_um, body_y0_um - bottom_taper_length_um - delta_length),
        ]
    )
    delta = abs(lower_access_path.length() - reference_path.length())
    lengths = {
        "arms": {
            "reference_access": float(reference_path.length()),
            "bottom_access": float(lower_access_path.length()),
        },
        "delta_length_um": float(delta),
    }
    path.write_text(json.dumps(lengths, indent=2) + "\n")


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    component = build_device().copy()
    component.flatten()
    component.write_gds(here / "device.gds")
    write_lengths_json(here / "lengths.json")
