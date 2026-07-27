from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Footprint and primary functional rails.
footprint_length = 120.0
footprint_width = 4.0
guide_width = 0.060
center_pitch = 0.100
transfer_length = 119.90
fixed_center_length = 119.90

# Upper/lower slotted slab section.
inner_rail_width = 0.066
inner_rail_pitch = 0.100
inner_rail_length = 104.25
inner_rail_x0 = 7.85
slab_height = 0.470
slab_taper_offset = 2.15
slab_x0_inner = 9.24
slab_x1_inner = 110.72
slab_x0_outer = 7.30
slab_x1_outer = 112.62

# Broad side-wall access geometry.
sidewall_width = 1.34
sidewall_taper_length = 1.25
sidewall_inner_gap = 0.88


def y_from_image(y_down: float) -> float:
    return footprint_width - y_down


def add_rect_ydown(
    component: gf.Component,
    x0: float,
    x1: float,
    y0_down: float,
    y1_down: float,
) -> None:
    width = x1 - x0
    height = y1_down - y0_down
    if width <= 0 or height <= 0:
        return
    rect = component << gf.components.rectangle(size=(width, height), layer=LAYER)
    rect.move((x0, y_from_image(y1_down)))


def add_tapered_band(
    component: gf.Component,
    y0_down: float,
    y1_down: float,
    x0_at_y0: float,
    x0_at_y1: float,
    x1_at_y0: float,
    x1_at_y1: float,
    slices: int = 36,
) -> None:
    dy = (y1_down - y0_down) / slices
    for index in range(slices):
        t0 = index / slices
        t1 = (index + 1) / slices
        xa = x0_at_y0 + (x0_at_y1 - x0_at_y0) * ((t0 + t1) / 2)
        xb = x1_at_y0 + (x1_at_y1 - x1_at_y0) * ((t0 + t1) / 2)
        add_rect_ydown(component, xa, xb, y0_down + index * dy, y0_down + (index + 1) * dy)


def add_tapered_rail(
    component: gf.Component,
    y0_down: float,
    y1_down: float,
    center_x0: float,
    center_x1: float,
    width0: float,
    width1: float,
    slices: int = 42,
) -> None:
    dy = (y1_down - y0_down) / slices
    for index in range(slices):
        t = (index + 0.5) / slices
        center = center_x0 + (center_x1 - center_x0) * t
        width = width0 + (width1 - width0) * t
        add_rect_ydown(
            component,
            center - width / 2,
            center + width / 2,
            y0_down + index * dy,
            y0_down + (index + 1) * dy,
        )


def add_straight_rail(
    component: gf.Component,
    x0: float,
    x1: float,
    y_down_center: float,
    width: float,
) -> None:
    path = gf.Path([(x0, y_from_image(y_down_center)), (x1, y_from_image(y_down_center))])
    rail = component << path.extrude(width=width, layer=LAYER)
    rail.move((0, 0))


def add_side_access(component: gf.Component, mirror_y: bool = False) -> None:
    if mirror_y:
        y0 = footprint_width - sidewall_taper_length
        y1 = footprint_width
        c_outer0, c_outer1 = 6.60, 4.85
        c_inner0, c_inner1 = 8.28, 7.10
        w0, w1 = 1.05, sidewall_width
    else:
        y0 = 0.0
        y1 = sidewall_taper_length
        c_outer0, c_outer1 = 4.85, 6.60
        c_inner0, c_inner1 = 7.10, 8.28
        w0, w1 = sidewall_width, 1.05

    # Left pair.
    add_tapered_rail(
        component,
        y0,
        y1,
        c_outer0,
        c_outer1,
        w0,
        w1,
    )
    add_tapered_rail(
        component,
        y0,
        y1,
        c_inner0,
        c_inner1,
        sidewall_width if not mirror_y else 1.25,
        1.25,
    )
    # Right pair.
    add_tapered_rail(
        component,
        y0,
        y1,
        footprint_length - c_inner0,
        footprint_length - c_inner1,
        sidewall_width if not mirror_y else 1.25,
        1.25,
    )
    add_tapered_rail(
        component,
        y0,
        y1,
        footprint_length - c_outer0,
        footprint_length - c_outer1,
        w0,
        w1,
    )


def add_upper_section(component: gf.Component) -> None:
    add_side_access(component, mirror_y=False)

    rail_centers = [0.798, 0.899, 0.998, 1.099, 1.199]
    for y_down in rail_centers:
        add_rect_ydown(
            component,
            inner_rail_x0,
            inner_rail_x0 + inner_rail_length,
            y_down - inner_rail_width / 2,
            y_down + inner_rail_width / 2,
        )

    add_tapered_band(
        component,
        1.245,
        1.735,
        slab_x0_outer,
        slab_x0_inner,
        slab_x1_outer,
        slab_x1_inner,
    )


def add_lower_section(component: gf.Component) -> None:
    add_side_access(component, mirror_y=True)

    rail_centers = [3.205, 3.104, 3.004, 2.904, 2.804]
    for y_down in rail_centers:
        add_rect_ydown(
            component,
            inner_rail_x0,
            inner_rail_x0 + inner_rail_length,
            y_down - inner_rail_width / 2,
            y_down + inner_rail_width / 2,
        )

    add_tapered_band(
        component,
        2.265,
        2.755,
        slab_x0_inner,
        slab_x0_outer,
        slab_x1_inner,
        slab_x1_outer,
    )


@gf.cell
def device() -> gf.Component:
    component = gf.Component()

    add_upper_section(component)
    add_lower_section(component)

    center_rails = [
        (1.806, fixed_center_length, 0.068),
        (1.905, fixed_center_length, 0.066),
        (2.007, transfer_length, guide_width),
        (2.107, fixed_center_length, 0.062),
        (2.209, fixed_center_length, 0.068),
    ]
    for y_down, length, width in center_rails:
        add_straight_rail(component, 0.03, length, y_down, width)

    return component


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    c = device().copy()
    c.flatten()
    c.write_gds(output_dir / "device.gds", with_metadata=False)
    lengths = {
        "arms": {
            "reference": 0.0,
            "transfer": transfer_length,
        },
        "delta_length_um": transfer_length,
    }
    (output_dir / "lengths.json").write_text(json.dumps(lengths, indent=2) + "\n")
