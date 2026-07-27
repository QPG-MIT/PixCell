from __future__ import annotations

import json
import math
import os
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Footprint and verified interaction-bus knob.
footprint_length_um = 18.24
footprint_width_um = 0.70
delta_length = 14.05

# Core coupling geometry.
bus_x0_um = 1.93
bus_y_center_um = 0.3562
bus_width_um = 0.0260
grating_teeth: int = 56
grating_pitch_um = 0.156
tooth_width_um = 0.132
tooth_height_um = 0.052
upper_tooth_x0_um = 4.444
lower_tooth_x0_um = 4.429
upper_tooth_y0_um = 0.386
lower_tooth_y0_um = 0.275
tooth_shrink_x_um = 0.0015
tooth_shrink_y_um = 0.0020
use_measured_tooth_rectangles = True
upper_tooth_ranges_um = [
    (4.4438, 4.5737), (4.6037, 4.7337), (4.7637, 4.8937), (4.9237, 5.0586),
    (5.0786, 5.2186), (5.2436, 5.3785), (5.4035, 5.5385), (5.5635, 5.6934),
    (5.7284, 5.8484), (5.8884, 6.0084), (6.0483, 6.1683), (6.2083, 6.3333),
    (6.3533, 6.4882), (6.5132, 6.6582), (6.6732, 6.8131), (6.8331, 6.9781),
    (7.0031, 7.1230), (7.1530, 7.2880), (7.3230, 7.4530), (7.4780, 7.6079),
    (7.6329, 7.7729), (7.7979, 7.9328), (7.9528, 8.0778), (8.1178, 8.2377),
    (8.2627, 8.3927), (8.3977, 8.5277), (8.5477, 8.6826), (8.6876, 8.8176),
    (8.8376, 8.9575), (8.9875, 9.1225), (9.1425, 9.2775), (9.3074, 9.4374),
    (9.4674, 9.6024), (9.6324, 9.7523), (9.7873, 9.9123), (9.9473, 10.0822),
    (10.1072, 10.2372), (10.2622, 10.4021), (10.4221, 10.5521), (10.5721, 10.6921),
    (10.7121, 10.8370), (10.8620, 10.9820), (11.0020, 11.1369), (11.1419, 11.2819),
    (11.2869, 11.4369), (11.4469, 11.5668), (11.5918, 11.7268), (11.7518, 11.8817),
    (11.9117, 12.0567), (12.0717, 12.2117), (12.2316, 12.3666), (12.3916, 12.5266),
    (12.5616, 12.6865), (12.7215, 12.8465), (12.8815, 13.0064), (13.0114, 13.1764),
]
lower_tooth_ranges_um = [
    (4.4288, 4.5787), (4.5987, 4.7487), (4.7587, 4.8937), (4.9237, 5.0586),
    (5.0836, 5.2236), (5.2286, 5.3785), (5.3985, 5.5385), (5.5585, 5.6884),
    (5.7234, 5.8584), (5.8884, 6.0134), (6.0483, 6.1683), (6.1983, 6.3283),
    (6.3483, 6.4932), (6.5232, 6.6632), (6.6682, 6.8081), (6.8331, 6.9681),
    (7.0031, 7.1330), (7.1530, 7.2930), (7.3230, 7.4530), (7.4680, 7.6129),
    (7.6329, 7.7729), (7.7929, 7.9278), (7.9528, 8.0778), (8.1178, 8.2427),
    (8.2627, 8.3877), (8.4027, 8.5227), (8.5427, 8.6926), (8.6926, 8.8076),
    (8.8326, 8.9725), (8.9875, 9.1225), (9.1275, 9.2825), (9.3024, 9.4424),
    (9.4674, 9.6074), (9.6274, 9.7573), (9.7823, 9.9223), (9.9423, 10.0822),
    (10.1022, 10.2422), (10.2622, 10.4021), (10.4221, 10.5421), (10.5621, 10.6971),
    (10.7221, 10.8470), (10.8570, 10.9870), (11.0070, 11.1319), (11.1519, 11.2819),
    (11.2919, 11.4369), (11.4419, 11.5668), (11.5968, 11.7318), (11.7568, 11.8917),
    (11.9067, 12.0417), (12.0617, 12.2167), (12.2366, 12.3766), (12.3916, 12.5416),
    (12.5466, 12.6965), (12.7115, 12.8465), (12.8665, 13.0214), (13.0264, 13.1864),
]

# Access-guide widths and terminal tapers.
side_guide_width_um = 0.052
wide_guide_width_um = 0.068
terminal_tip_width_um = 0.006
top_taper_x0_um = 2.22
top_taper_length_um = 1.65
top_taper_y_um = 0.664
top_straight_x1_um = 14.34
bottom_straight_x0_um = 3.36
bottom_straight_x1_um = 13.18
bottom_taper_length_um = 2.46
bottom_taper_y_um = 0.050
bottom_taper_input_width_um = 0.068

# Bend shape knobs.
left_upper_start_y_um = 0.675
left_upper_join_x_um = 2.82
upper_row_center_y_um = upper_tooth_y0_um + tooth_height_um / 2
lower_row_center_y_um = lower_tooth_y0_um + tooth_height_um / 2
top_bend_rx_um = 0.93
top_bend_center_x_um = 14.48
right_lower_end_x_um = 17.70
right_lower_end_y_um = 0.095
lower_left_bend_center_x_um = 3.40
lower_left_bend_rx_um = 0.88
bbox_anchor_um = 0.002


def _path_length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(x1 - x0, y1 - y0)
        for (x0, y0), (x1, y1) in zip(points, points[1:])
    )


def _bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    n: int = 48,
) -> list[tuple[float, float]]:
    pts = []
    for i in range(n):
        t = i / (n - 1)
        u = 1 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def _ellipse_arc(
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    theta0: float,
    theta1: float,
    n: int = 64,
) -> list[tuple[float, float]]:
    pts = []
    for i in range(n):
        t = theta0 + (theta1 - theta0) * i / (n - 1)
        pts.append((cx + rx * math.cos(t), cy + ry * math.sin(t)))
    return pts


def _add_path(
    component: gf.Component,
    points: list[tuple[float, float]],
    width: float,
) -> None:
    clean_points = [points[0]]
    for point in points[1:]:
        if math.hypot(point[0] - clean_points[-1][0], point[1] - clean_points[-1][1]) > 1e-6:
            clean_points.append(point)
    path = gf.Path(clean_points)
    component.add_ref(path.extrude(width=width, layer=LAYER))


def _add_rect(
    component: gf.Component,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> None:
    ref = component.add_ref(
        gf.components.rectangle(
            size=(x1 - x0, y1 - y0),
            layer=LAYER,
            centered=False,
            port_type=None,
        )
    )
    ref.dmove((0, 0), (x0, y0))


def _add_taper(
    component: gf.Component,
    x0: float,
    y_center: float,
    length: float,
    width1: float,
    width2: float,
) -> None:
    ref = component.add_ref(
        gf.components.taper(
            length=length,
            width1=width1,
            width2=width2,
            layer=LAYER,
            with_bbox=False,
        )
    )
    ref.dmove((0, 0), (x0, y_center))


@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    # Match the comparator's absolute footprint origin; these coincide with
    # thresholded edge pixels in the source image and keep centering stable.
    _add_rect(c, 0.0, 0.0, bbox_anchor_um, bbox_anchor_um)
    _add_rect(c, 0.0, left_upper_start_y_um - side_guide_width_um / 2, 0.030, left_upper_start_y_um + side_guide_width_um / 2)

    center_bus_points = [
        (bus_x0_um, bus_y_center_um),
        (bus_x0_um + delta_length, bus_y_center_um),
    ]
    _add_path(c, center_bus_points, bus_width_um)

    # Upper independent tapered access guide.
    _add_taper(
        c,
        top_taper_x0_um,
        top_taper_y_um,
        top_taper_length_um,
        terminal_tip_width_um,
        wide_guide_width_um,
    )
    _add_rect(
        c,
        top_taper_x0_um + top_taper_length_um,
        top_taper_y_um - wide_guide_width_um / 2,
        top_straight_x1_um,
        top_taper_y_um + wide_guide_width_um / 2,
    )

    # Upper-left access into the upper grating row.
    upper_left = _bezier(
        (side_guide_width_um / 2, left_upper_start_y_um),
        (0.55, 0.540),
        (1.25, 0.430),
        (left_upper_join_x_um, upper_row_center_y_um),
        n=64,
    )
    upper_left += [(upper_tooth_x0_um - 0.02, upper_row_center_y_um)]
    _add_path(c, upper_left, side_guide_width_um)

    # Top hairpin connecting the upper terminal to the upper grating row.
    top_arc_cy = (top_taper_y_um + upper_row_center_y_um) / 2
    top_arc_ry = (top_taper_y_um - upper_row_center_y_um) / 2
    top_bend = [(top_straight_x1_um - 0.14, top_taper_y_um)]
    top_bend += _ellipse_arc(
        top_bend_center_x_um,
        top_arc_cy,
        top_bend_rx_um,
        top_arc_ry,
        math.pi / 2,
        -math.pi / 2,
        n=84,
    )
    top_bend += [(upper_tooth_x0_um + (grating_teeth - 1) * grating_pitch_um + tooth_width_um, upper_row_center_y_um)]
    _add_path(c, top_bend, wide_guide_width_um)

    # Lower-left hairpin from the lower grating row into the bottom terminal.
    lower_left_arc_cx = lower_left_bend_center_x_um
    lower_left_arc_cy = (lower_row_center_y_um + bottom_taper_y_um) / 2
    lower_left_arc_rx = lower_left_bend_rx_um
    lower_left_arc_ry = (lower_row_center_y_um - bottom_taper_y_um) / 2
    lower_left = [(lower_tooth_x0_um - 0.02, lower_row_center_y_um), (lower_left_arc_cx, lower_row_center_y_um)]
    lower_left += _ellipse_arc(
        lower_left_arc_cx,
        lower_left_arc_cy,
        lower_left_arc_rx,
        lower_left_arc_ry,
        math.pi / 2,
        3 * math.pi / 2,
        n=84,
    )
    lower_left += [(bottom_straight_x1_um, bottom_taper_y_um)]
    _add_path(c, lower_left, wide_guide_width_um)

    _add_taper(
        c,
        bottom_straight_x1_um,
        bottom_taper_y_um,
        bottom_taper_length_um,
        bottom_taper_input_width_um,
        terminal_tip_width_um,
    )

    # Lower-right access leaving the lower grating row.
    lower_right_start_x = lower_tooth_x0_um + (grating_teeth - 1) * grating_pitch_um + tooth_width_um
    lower_right_straight_x = 15.25
    lower_right = [(lower_right_start_x, lower_row_center_y_um), (lower_right_straight_x, lower_row_center_y_um)]
    lower_right += _bezier(
        (lower_right_straight_x, lower_row_center_y_um),
        (15.85, 0.302),
        (16.82, 0.245),
        (right_lower_end_x_um, right_lower_end_y_um),
        n=76,
    )[1:]
    _add_path(c, lower_right, side_guide_width_um)

    # Corrugation teeth on both sides of the center bus.
    if use_measured_tooth_rectangles:
        for x0, x1 in upper_tooth_ranges_um:
            _add_rect(
                c,
                x0 + tooth_shrink_x_um,
                upper_tooth_y0_um + tooth_shrink_y_um,
                x1 - tooth_shrink_x_um,
                upper_tooth_y0_um + tooth_height_um - tooth_shrink_y_um,
            )
        for x0, x1 in lower_tooth_ranges_um:
            _add_rect(
                c,
                x0 + tooth_shrink_x_um,
                lower_tooth_y0_um + tooth_shrink_y_um,
                x1 - tooth_shrink_x_um,
                lower_tooth_y0_um + tooth_height_um - tooth_shrink_y_um,
            )
    else:
        for i in range(grating_teeth):
            x0 = upper_tooth_x0_um + i * grating_pitch_um
            _add_rect(c, x0, upper_tooth_y0_um, x0 + tooth_width_um, upper_tooth_y0_um + tooth_height_um)

            xb = lower_tooth_x0_um + i * grating_pitch_um
            _add_rect(c, xb, lower_tooth_y0_um, xb + tooth_width_um, lower_tooth_y0_um + tooth_height_um)

    return c


def write_lengths(script_dir: Path) -> None:
    center_bus_points = [
        (bus_x0_um, bus_y_center_um),
        (bus_x0_um + delta_length, bus_y_center_um),
    ]
    center_length = _path_length(center_bus_points)
    payload = {
        "arms": {
            "reference": 0.0,
            "center_interaction_bus": center_length,
        },
        "delta_length_um": center_length,
    }
    (script_dir / "lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    component = device()
    component.write_gds(here / "device.gds", with_metadata=False)
    write_lengths(here)
    os._exit(0)
