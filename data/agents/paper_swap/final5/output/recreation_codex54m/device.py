from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

# Function-defining tunables.
tip_width_um = 0.01
tip_length_um = 2.25
loop_width_um = 0.052
bus_width_um = 0.024
bus_gap_um = 0.012
tooth_depth_um = 0.0135
tooth_width_um = 0.113
tooth_period_um = 0.16
num_teeth = 56
top_arm_extension_um = 0.0

# Placement tunables.
top_tip_x_um = 1.08
top_body_start_x_um = 2.18
top_outer_y_um = 0.026
top_left_open_x_um = 0.05
top_right_turn_x_um = 18.05
top_coupler_y_um = 0.282
top_coupler_start_x_um = 1.82
top_coupler_end_x_um = 15.07

bottom_right_open_x_um = 18.18
bottom_coupler_start_x_um = 3.09
bottom_coupler_y_um = 0.42
bottom_left_turn_x_um = 1.2
bottom_outer_y_um = 0.662
bottom_body_end_x_um = 15.35
bottom_tip_end_x_um = 16.28

bus_start_x_um = 1.94
bus_end_x_um = 15.97
bus_center_y_um = 0.355

tooth_start_x_um = 4.455


def smooth_path(points: list[tuple[float, float]], radius: float) -> gf.Path:
    return gf.path.smooth(points=points, radius=radius)


def place_rect(component: gf.Component, size: tuple[float, float], origin: tuple[float, float]) -> None:
    rect = component << gf.components.rectangle(size=size, layer=LAYER)
    rect.move(origin)


@gf.cell
def build_device() -> gf.Component:
    c = gf.Component("recreated_device")
    bus_xs = gf.cross_section.cross_section(width=bus_width_um, layer=LAYER)

    top_points = [
        (top_body_start_x_um, top_outer_y_um),
        (top_coupler_end_x_um + 1.6, top_outer_y_um),
        (top_right_turn_x_um, 0.155),
        (top_coupler_end_x_um, top_coupler_y_um),
        (top_coupler_start_x_um, top_coupler_y_um),
        (top_left_open_x_um, 0.15),
        (top_left_open_x_um, 0.03),
    ]
    bottom_points = [
        (bottom_right_open_x_um, 0.67),
        (bottom_body_end_x_um + 2.3, 0.55),
        (bus_end_x_um + 0.22, bottom_coupler_y_um),
        (bottom_coupler_start_x_um, bottom_coupler_y_um),
        (bottom_left_turn_x_um, 0.52),
        (3.6, bottom_outer_y_um),
        (bottom_body_end_x_um, bottom_outer_y_um),
    ]

    top_path = smooth_path(top_points, radius=0.08)
    bottom_path = smooth_path(bottom_points, radius=0.08)

    top_ref = c << gf.path.extrude(top_path, width=loop_width_um, layer=LAYER)
    bottom_ref = c << gf.path.extrude(bottom_path, width=loop_width_um, layer=LAYER)
    _ = (top_ref, bottom_ref)

    top_taper = c << gf.components.taper(
        length=tip_length_um,
        width1=tip_width_um,
        width2=loop_width_um,
        layer=LAYER,
        with_bbox=False,
    )
    top_taper.connect("o2", top_ref.ports["o1"])

    bottom_taper = c << gf.components.taper(
        length=tip_length_um,
        width1=loop_width_um,
        width2=tip_width_um,
        layer=LAYER,
        with_bbox=False,
    )
    bottom_taper.connect("o1", bottom_ref.ports["o2"])

    bus = c << gf.components.straight(
        length=bus_end_x_um - bus_start_x_um,
        cross_section=bus_xs,
    )
    bus.move((bus_start_x_um, bus_center_y_um - bus_width_um / 2))

    top_inner_edge_y = top_coupler_y_um + loop_width_um / 2
    bottom_inner_edge_y = bottom_coupler_y_um - loop_width_um / 2 - tooth_depth_um
    if top_arm_extension_um > 0:
        place_rect(
            c,
            (top_arm_extension_um, loop_width_um),
            (top_left_open_x_um - top_arm_extension_um, 0.03 - loop_width_um / 2),
        )
    for index in range(num_teeth):
        tooth_x = tooth_start_x_um + index * tooth_period_um
        place_rect(c, (tooth_width_um, tooth_depth_um), (tooth_x, top_inner_edge_y))
        place_rect(c, (tooth_width_um, tooth_depth_um), (tooth_x, bottom_inner_edge_y))

    c.flatten()
    c.info["arm_lengths_um"] = {
        "top_arm": float(top_path.length() + top_arm_extension_um),
        "bottom_arm": float(bottom_path.length()),
    }
    return c


if __name__ == "__main__":
    gf.clear_cache()
    component = build_device()
    out_dir = Path(__file__).resolve().parent
    gds_path = out_dir / "device.gds"
    component.write_gds(gds_path, with_metadata=False)

    arms = component.info["arm_lengths_um"]
    payload = {
        "arms": arms,
        "delta_length_um": abs(arms["top_arm"] - arms["bottom_arm"]),
    }
    (out_dir / "lengths.json").write_text(json.dumps(payload, indent=2))
