from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf


footprint_length_um = 120.0
footprint_height_um = 4.0
layer = (1, 0)

trace_width_um = 0.066
track_pitch_um = 0.100
bank_trace_count: int = 5
center_trace_count: int = 5

lead_center_x_um = 7.10
turn_radius_um = 0.72

upper_bank_base_y_um = 2.800
center_bundle_base_y_um = 1.792
lower_bank_base_y_um = 0.798

upper_fill_center_y_um = 2.499
lower_fill_center_y_um = 1.501
upper_fill_width_um = 0.468
lower_fill_width_um = 0.468

delta_length = 0.0

arc_samples: int = 24


def arc_points(
    center: tuple[float, float],
    radius: float,
    start_deg: float,
    stop_deg: float,
    samples: int,
) -> list[tuple[float, float]]:
    points = []
    for i in range(samples + 1):
        t = i / samples
        angle = math.radians(start_deg + (stop_deg - start_deg) * t)
        points.append(
            (center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle))
        )
    return points


def rounded_u_points(
    *,
    x_left: float,
    x_right: float,
    y_start: float,
    y_end: float,
    y_center: float,
    radius: float,
    upper: bool,
    samples: int,
) -> list[tuple[float, float]]:
    if upper:
        first_corner_y = y_center + radius
        second_corner_y = y_center + radius
        points = [(x_left, y_start), (x_left, first_corner_y)]
        points.extend(
            arc_points((x_left + radius, y_center + radius), radius, 180.0, 270.0, samples)[1:]
        )
        points.append((x_right - radius, y_center))
        points.extend(
            arc_points((x_right - radius, y_center + radius), radius, 270.0, 360.0, samples)[1:]
        )
        points.append((x_right, y_end))
        return points

    first_corner_y = y_center - radius
    second_corner_y = y_center - radius
    points = [(x_left, y_start), (x_left, first_corner_y)]
    points.extend(
        arc_points((x_left + radius, y_center - radius), radius, 180.0, 90.0, samples)[1:]
    )
    points.append((x_right - radius, y_center))
    points.extend(
        arc_points((x_right - radius, y_center - radius), radius, 90.0, 0.0, samples)[1:]
    )
    points.append((x_right, y_end))
    return points


def extruded_path(points: list[tuple[float, float]], width_um: float) -> tuple[gf.Component, float]:
    path = gf.Path(points)
    component = path.extrude(width=width_um, layer=layer)
    return component, float(path.length())


@gf.cell
def build_device() -> gf.Component:
    c = gf.Component("paper_swap_final8_recreation")

    x_left = lead_center_x_um
    x_right = footprint_length_um - lead_center_x_um

    upper_lengths: list[float] = []
    lower_lengths: list[float] = []

    for idx in range(bank_trace_count):
        y_center = upper_bank_base_y_um + idx * track_pitch_um
        top_points = rounded_u_points(
            x_left=x_left,
            x_right=x_right,
            y_start=footprint_height_um + (delta_length if idx == bank_trace_count - 1 else 0.0),
            y_end=footprint_height_um,
            y_center=y_center,
            radius=turn_radius_um,
            upper=True,
            samples=arc_samples,
        )
        top_component, top_length = extruded_path(top_points, trace_width_um)
        c.add_ref(top_component)
        upper_lengths.append(top_length)

    top_fill_points = rounded_u_points(
        x_left=x_left,
        x_right=x_right,
        y_start=footprint_height_um,
        y_end=footprint_height_um,
        y_center=upper_fill_center_y_um,
        radius=turn_radius_um,
        upper=True,
        samples=arc_samples,
    )
    top_fill_component, _ = extruded_path(top_fill_points, upper_fill_width_um)
    c.add_ref(top_fill_component)

    for idx in range(center_trace_count):
        y_center = center_bundle_base_y_um + idx * track_pitch_um
        center_component, _ = extruded_path(
            [(0.0, y_center), (footprint_length_um, y_center)], trace_width_um
        )
        c.add_ref(center_component)

    bottom_fill_points = rounded_u_points(
        x_left=x_left,
        x_right=x_right,
        y_start=0.0,
        y_end=0.0,
        y_center=lower_fill_center_y_um,
        radius=turn_radius_um,
        upper=False,
        samples=arc_samples,
    )
    bottom_fill_component, _ = extruded_path(bottom_fill_points, lower_fill_width_um)
    c.add_ref(bottom_fill_component)

    for idx in range(bank_trace_count):
        y_center = lower_bank_base_y_um + idx * track_pitch_um
        bottom_points = rounded_u_points(
            x_left=x_left,
            x_right=x_right,
            y_start=0.0,
            y_end=0.0,
            y_center=y_center,
            radius=turn_radius_um,
            upper=False,
            samples=arc_samples,
        )
        bottom_component, bottom_length = extruded_path(bottom_points, trace_width_um)
        c.add_ref(bottom_component)
        lower_lengths.append(bottom_length)

    arm_top = upper_lengths[-1]
    arm_bottom = lower_lengths[0]
    lengths_payload = {
        "arms": {
            "upper_outer_arm_um": arm_top,
            "lower_outer_arm_um": arm_bottom,
        },
        "delta_length_um": abs(arm_top - arm_bottom),
    }
    out_dir = Path(__file__).resolve().parent
    (out_dir / "lengths.json").write_text(json.dumps(lengths_payload, indent=2))

    return c


if __name__ == "__main__":
    component = build_device()
    top = gf.Component("top")
    top.add_ref(component)
    top.flatten()
    top.write_gds(Path(__file__).resolve().parent / "device.gds")
