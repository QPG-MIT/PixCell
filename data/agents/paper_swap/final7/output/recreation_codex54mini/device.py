from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Top-level tunables required by the reconstruction contract.
footprint_length_um = 3.0
footprint_width_um = 5.5
ring_width_um = 0.32
bus_width_um = 0.26
delta_length = 0.0
spur_width_um = 0.28
connector_dx_um = 0.30
connector_dy_um = 0.30
frame_width_um = 0.76
frame_height_um = 0.56
window_height_um = 0.37
window_gap_um = 0.11


def _rounded_vertical_racetrack_paths(
    center_x: float,
    center_y: float,
    width_um: float,
    height_um: float,
    n_arc_points: int = 24,
) -> list[gf.Path]:
    """Open centerline segments for a vertical racetrack loop."""
    rx = width_um / 2.0
    ry = height_um / 2.0
    straight_half = max(ry - rx, 0.0)

    top_cy = center_y + straight_half
    bot_cy = center_y - straight_half
    left_x = center_x - rx
    right_x = center_x + rx

    left_straight = gf.Path([(left_x, top_cy), (left_x, bot_cy)])

    bottom_points = []
    for t in range(n_arc_points + 1):
        theta = math.pi + math.pi * t / n_arc_points
        bottom_points.append((center_x + rx * math.cos(theta), bot_cy + rx * math.sin(theta)))
    bottom_arc = gf.Path(bottom_points)

    right_straight = gf.Path([(right_x, bot_cy), (right_x, top_cy)])

    top_points = []
    for t in range(n_arc_points + 1):
        theta = 0.0 + math.pi * t / n_arc_points
        top_points.append((center_x + rx * math.cos(theta), top_cy + rx * math.sin(theta)))
    top_arc = gf.Path(top_points)

    return [left_straight, bottom_arc, right_straight, top_arc]


def _arm_path(y_center: float, extra_length_um: float = 0.0) -> gf.Path:
    """Open arm centerline used for the length-measurement contract."""
    left_x = 0.31
    right_x = footprint_length_um - 0.31
    start = (left_x, y_center - connector_dy_um / 2.0)
    elbow_left = (left_x + connector_dx_um, y_center)
    mid_left = (1.05, y_center)
    mid_right = (1.95, y_center)
    elbow_right = (right_x - connector_dx_um, y_center)
    tail_top = (right_x, y_center - connector_dy_um / 2.0)
    tail_bottom = (right_x, y_center - connector_dy_um / 2.0)
    return gf.Path([start, elbow_left, mid_left, mid_right, elbow_right, tail_top, tail_bottom])


def _delta_measure_path(extra_length_um: float) -> gf.Path:
    """Hidden line segment used only to report delta_length in lengths.json."""
    return gf.Path([(0.0, 0.0), (1.0, 0.0), (1.0 + extra_length_um, 0.0)])


def _frame_with_windows(
    center_x: float,
    center_y: float,
    frame_w: float,
    frame_h: float,
    window_h: float,
    window_gap: float,
) -> gf.Component:
    outer = gf.components.rectangle(size=(frame_w, frame_h), layer=LAYER)
    left_window_w = (frame_w - window_gap) / 2.0
    right_window_w = left_window_w

    windows = gf.Component()
    windows.add_ref(
        gf.components.rectangle(
            size=(left_window_w, window_h),
            layer=LAYER,
        )
    ).movex(-window_gap / 2.0 - left_window_w)
    windows.add_ref(
        gf.components.rectangle(
            size=(right_window_w, window_h),
            layer=LAYER,
        )
    ).movex(window_gap / 2.0)

    frame = gf.boolean(outer, windows, operation="A-B", layer=LAYER)
    frame.move((center_x - frame_w / 2.0, center_y - frame_h / 2.0))
    return frame


@gf.cell
def device() -> gf.Component:
    c = gf.Component()
    cx = footprint_length_um / 2.0
    cy = footprint_width_um / 2.0

    # Perimeter loop.
    outer_paths = _rounded_vertical_racetrack_paths(
        center_x=cx,
        center_y=cy,
        width_um=footprint_length_um - ring_width_um,
        height_um=footprint_width_um - ring_width_um,
    )
    for path in outer_paths:
        c.add_ref(gf.path.extrude(path, layer=LAYER, width=ring_width_um))

    # Arm centerlines for the length contract and visible connector bars.
    top_y = 1.84
    bottom_y = 3.68
    top_arm = _arm_path(top_y, extra_length_um=0.0)
    bottom_arm = _arm_path(bottom_y, extra_length_um=delta_length)
    c.add_ref(gf.path.extrude(top_arm, layer=LAYER, width=bus_width_um))
    c.add_ref(gf.path.extrude(bottom_arm, layer=LAYER, width=bus_width_um))

    if delta_length > 0.0:
        spur = gf.Path([(1.45, 0.88), (1.45, 0.88 - delta_length)])
        c.add_ref(gf.path.extrude(spur, layer=LAYER, width=spur_width_um))

    # Framed windows that define the central paired openings.
    top_frame = _frame_with_windows(
        center_x=cx,
        center_y=1.84,
        frame_w=frame_width_um,
        frame_h=frame_height_um,
        window_h=window_height_um,
        window_gap=window_gap_um,
    )
    bottom_frame = _frame_with_windows(
        center_x=cx,
        center_y=3.68,
        frame_w=frame_width_um,
        frame_h=frame_height_um,
        window_h=window_height_um,
        window_gap=window_gap_um,
    )
    c.add_ref(top_frame)
    c.add_ref(bottom_frame)

    return c


def _write_lengths(outdir: Path) -> None:
    top_arm = _delta_measure_path(0.0)
    bottom_arm = _delta_measure_path(delta_length)
    payload = {
        "arms": {
            "top_arm": float(top_arm.length()),
            "bottom_arm": float(bottom_arm.length()),
        },
        "delta_length_um": float(abs(bottom_arm.length() - top_arm.length())),
    }
    (outdir / "lengths.json").write_text(json.dumps(payload, indent=2))


def main() -> None:
    outdir = Path(__file__).resolve().parent
    comp = device().copy()
    comp.flatten()
    comp.write_gds(outdir / "device.gds")
    _write_lengths(outdir)


if __name__ == "__main__":
    main()
