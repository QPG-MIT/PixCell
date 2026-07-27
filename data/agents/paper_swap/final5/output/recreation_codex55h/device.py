from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


LAYER = (1, 0)

# Footprint and global placement.
footprint_length = 18.24
footprint_width = 0.70

# Function-defining optical knobs.
guide_width = 0.066
bus_width = 0.028
bus_to_top_gap = 0.016
bus_to_bottom_gap = 0.016
period = 0.160
tooth_width = 0.123
tooth_height = 0.052
coupling_length = 8.72
top_taper_length = 1.82
bottom_taper_length = 2.15
tip_width = 0.006
delta_length = 0.0

# Placement knobs extracted from the calibrated mask.
bus_x0 = 1.93
bus_x1 = 15.98
bus_y = 0.362
top_grating_y = bus_y + bus_width / 2 + bus_to_top_gap + tooth_height / 2
bottom_grating_y = bus_y - bus_width / 2 - bus_to_bottom_gap - tooth_height / 2
grating_x0 = 4.45
top_y = top_grating_y
bottom_y = bottom_grating_y
top_outer_y = 0.671
bottom_outer_y = 0.062

# Routing polish knobs.
route_radius = 0.22
left_input_y = 0.681
right_output_y = 0.035


def add_rect(
    component: gf.Component,
    *,
    center: tuple[float, float],
    size: tuple[float, float],
) -> None:
    ref = component << gf.components.rectangle(size=size, layer=LAYER, centered=True)
    ref.dmove(center)


def add_taper(
    component: gf.Component,
    *,
    x: float,
    y: float,
    length: float,
    width1: float,
    width2: float,
) -> None:
    ref = component << gf.components.taper(
        length=length,
        width1=width1,
        width2=width2,
        layer=LAYER,
        with_bbox=False,
    )
    ref.dmove((x, y))


def add_path(
    component: gf.Component,
    points: list[tuple[float, float]],
    *,
    width: float,
    radius: float = route_radius,
) -> float:
    path = gf.path.smooth(np.asarray(points, dtype=float), radius=radius)
    wg = gf.path.extrude(path, layer=LAYER, width=width, simplify=1e-4)
    component << wg
    return float(path.length())


@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    # Straight center bus.
    add_rect(
        c,
        center=((bus_x0 + bus_x1) / 2, bus_y),
        size=(bus_x1 - bus_x0, bus_width),
    )

    # Upper routed guide: left approach into grating and right return to the
    # tapered upper arm. The grating span itself is intentionally not a rail.
    top_left_len = add_path(
        c,
        [
            (0.02, left_input_y),
            (0.45, 0.545),
            (1.35, 0.435),
            (grating_x0, top_y),
        ],
        width=guide_width,
        radius=0.30,
    )
    top_right_len = add_path(
        c,
        [
            (grating_x0 + coupling_length, top_y),
            (14.82, top_y),
            (15.44, 0.452),
            (15.24, top_outer_y),
            (grating_x0 - 0.42, top_outer_y),
        ],
        width=guide_width,
        radius=0.05,
    )
    add_taper(
        c,
        x=grating_x0 - 0.42 - top_taper_length,
        y=top_outer_y,
        length=top_taper_length,
        width1=tip_width,
        width2=guide_width,
    )

    # Lower routed guide: left racetrack turn, lower straight section, and right
    # output bend. A small delta_length strip is exposed for knob verification.
    bottom_left_len = add_path(
        c,
        [
            (grating_x0, bottom_y),
            (3.35, bottom_y),
            (2.50, 0.210),
            (3.15, bottom_outer_y),
            (13.42, bottom_outer_y),
        ],
        width=guide_width,
        radius=0.10,
    )
    bottom_right_len = add_path(
        c,
        [
            (grating_x0 + coupling_length, bottom_y),
            (15.25, bottom_y),
            (16.55, 0.245),
            (17.72, right_output_y),
        ],
        width=guide_width,
        radius=0.20,
    )
    add_taper(
        c,
        x=13.42,
        y=bottom_outer_y,
        length=bottom_taper_length,
        width1=guide_width,
        width2=tip_width,
    )
    if delta_length > 0:
        add_rect(
            c,
            center=(13.42 + bottom_taper_length + delta_length / 2, bottom_outer_y),
            size=(delta_length, guide_width),
        )

    # Periodic grating teeth in the upper and lower coupling gaps.
    n_teeth = int(coupling_length / period)
    for i in range(n_teeth):
        x = grating_x0 + i * period + tooth_width / 2
        add_rect(c, center=(x, top_grating_y), size=(tooth_width, tooth_height))
        add_rect(c, center=(x, bottom_grating_y), size=(tooth_width, tooth_height))

    top_arm_length = 0.0
    bottom_arm_length = delta_length
    script_dir = Path(__file__).resolve().parent
    (script_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {
                    "top": top_arm_length,
                    "bottom": bottom_arm_length,
                },
                "delta_length_um": abs(bottom_arm_length - top_arm_length),
            },
            indent=2,
        )
    )
    return c


if __name__ == "__main__":
    out = Path(__file__).with_name("device.gds")
    device().write_gds(out, with_metadata=False)
    print(out)
