from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


LAYER = (1, 0)

# Footprint and placement knobs
footprint_length = 120.0
footprint_height = 4.0

# Function-defining directional-coupler knobs
coupling_length = 56.5
nominal_coupling_length = 56.5
coupling_gap = 0.16
top_width = 0.36
bottom_width = 0.24

# Port and taper knobs
taper_length = 10.0
top_port_tip_width = 0.30
bottom_port_tip_width = 0.30
top_left_bend_width = 1.00
top_right_bend_width = 1.05
bottom_left_bend_width = 0.65
bottom_right_bend_width = 0.90
top_right_bend_x_shift = -0.60
bottom_left_bend_x_shift = 0.50

# Routing knobs
top_left_port_y = 3.73
top_right_port_y = 3.825
bottom_left_port_y = 0.284
bottom_right_port_y = 0.165
top_coupler_y = 2.22
left_coupler_x = 31.5
right_bend_length = 14.0
left_s_bend_start_x = 17.0
left_s_bend_radius = 5.5
right_s_bend_radius = 5.5
sample_points_per_bend = 48

gds_filename = "device.gds"


def smoothstep(t: np.ndarray) -> np.ndarray:
    return t * t * (3.0 - 2.0 * t)


def bend_points(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    n: int,
) -> list[tuple[float, float]]:
    xs = np.linspace(x0, x1, n)
    t = np.linspace(0.0, 1.0, n)
    ys = y0 + (y1 - y0) * smoothstep(t)
    return list(zip(xs.tolist(), ys.tolist(), strict=True))


def bezier_points(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    n: int,
) -> list[tuple[float, float]]:
    t = np.linspace(0.0, 1.0, n)
    u = 1.0 - t
    x = (
        u**3 * p0[0]
        + 3.0 * u**2 * t * p1[0]
        + 3.0 * u * t**2 * p2[0]
        + t**3 * p3[0]
    )
    y = (
        u**3 * p0[1]
        + 3.0 * u**2 * t * p1[1]
        + 3.0 * u * t**2 * p2[1]
        + t**3 * p3[1]
    )
    return list(zip(x.tolist(), y.tolist(), strict=True))


def path_length(points: list[tuple[float, float]]) -> float:
    arr = np.array(points, dtype=float)
    delta = np.diff(arr, axis=0)
    return float(np.linalg.norm(delta, axis=1).sum())


def make_transition_segment(
    points: list[tuple[float, float]],
    width1: float,
    width2: float,
) -> gf.Component:
    xs1 = gf.cross_section.strip(width=width1, layer=LAYER)
    xs2 = gf.cross_section.strip(width=width2, layer=LAYER)
    transition = gf.path.transition(xs1, xs2, width_type="linear")
    return gf.path.extrude_transition(gf.Path(points), transition)


def make_route(points: list[tuple[float, float]], width: float) -> gf.Component:
    return gf.path.extrude(gf.Path(points), width=width, layer=LAYER, simplify=1e-4)


def active_footprint_length() -> float:
    return footprint_length + (coupling_length - nominal_coupling_length)


def top_route_points() -> list[tuple[float, float]]:
    right_coupler_x = left_coupler_x + coupling_length
    right_end_x = right_coupler_x + right_bend_length
    active_length = active_footprint_length()
    points: list[tuple[float, float]] = []
    points.extend(
        [
            (taper_length, top_left_port_y),
            (left_s_bend_start_x, top_left_port_y),
            (22.95, 3.45),
            (24.25, 3.30),
            (24.91, 3.15),
            (25.19, 3.00),
            (25.35, 2.85),
            (25.83, 2.70),
            (26.93, 2.55),
            (29.80, 2.40),
            (left_coupler_x, top_coupler_y),
        ]
    )
    points.append((right_coupler_x, top_coupler_y))
    points.extend(
        [
            (right_coupler_x + 2.03 + top_right_bend_x_shift, 2.40),
            (right_coupler_x + 4.40 + top_right_bend_x_shift, 2.55),
            (right_coupler_x + 5.48 + top_right_bend_x_shift, 2.70),
            (right_coupler_x + 6.11 + top_right_bend_x_shift, 2.85),
            (right_coupler_x + 6.33 + top_right_bend_x_shift, 3.00),
            (right_coupler_x + 6.49 + top_right_bend_x_shift, 3.15),
            (right_coupler_x + 7.03 + top_right_bend_x_shift, 3.30),
            (right_coupler_x + 7.85 + top_right_bend_x_shift, 3.45),
            (right_coupler_x + 9.60 + top_right_bend_x_shift, 3.60),
            (right_end_x, top_right_port_y),
        ]
    )
    points.append((active_length - taper_length, top_right_port_y))
    return points


def top_left_bend_points() -> list[tuple[float, float]]:
    return [
        (left_s_bend_start_x, top_left_port_y),
        (22.95, 3.45),
        (24.25, 3.30),
        (24.91, 3.15),
        (25.19, 3.00),
        (25.35, 2.85),
        (25.83, 2.70),
        (26.93, 2.55),
        (29.80, 2.40),
        (left_coupler_x, top_coupler_y),
    ]


def top_right_bend_points() -> list[tuple[float, float]]:
    right_coupler_x = left_coupler_x + coupling_length
    right_end_x = right_coupler_x + right_bend_length
    return [
        (right_coupler_x, top_coupler_y),
        (right_coupler_x + 2.03 + top_right_bend_x_shift, 2.40),
        (right_coupler_x + 4.40 + top_right_bend_x_shift, 2.55),
        (right_coupler_x + 5.48 + top_right_bend_x_shift, 2.70),
        (right_coupler_x + 6.11 + top_right_bend_x_shift, 2.85),
        (right_coupler_x + 6.33 + top_right_bend_x_shift, 3.00),
        (right_coupler_x + 6.49 + top_right_bend_x_shift, 3.15),
        (right_coupler_x + 7.03 + top_right_bend_x_shift, 3.30),
        (right_coupler_x + 7.85 + top_right_bend_x_shift, 3.45),
        (right_coupler_x + 9.60 + top_right_bend_x_shift, 3.60),
        (right_end_x, top_right_port_y),
    ]


def bottom_route_points() -> list[tuple[float, float]]:
    bottom_coupler_y = top_coupler_y - coupling_gap - (top_width + bottom_width) / 2.0
    left_bend_start_x = 19.5
    right_coupler_x = left_coupler_x + coupling_length
    right_end_x = right_coupler_x + right_bend_length
    active_length = active_footprint_length()
    points: list[tuple[float, float]] = []
    points.extend(
        [
            (taper_length, bottom_left_port_y),
            (left_bend_start_x, bottom_left_port_y),
            (20.99 + bottom_left_bend_x_shift, 0.40),
            (23.27 + bottom_left_bend_x_shift, 0.55),
            (24.44 + bottom_left_bend_x_shift, 0.70),
            (25.04 + bottom_left_bend_x_shift, 0.85),
            (25.35 + bottom_left_bend_x_shift, 1.00),
            (25.48 + bottom_left_bend_x_shift, 1.15),
            (25.99 + bottom_left_bend_x_shift, 1.30),
            (26.97 + bottom_left_bend_x_shift, 1.45),
            (28.83 + bottom_left_bend_x_shift, 1.60),
            (left_coupler_x, bottom_coupler_y),
        ]
    )
    points.append((right_coupler_x, bottom_coupler_y))
    points.extend(
        [
            (right_coupler_x + 2.00, 1.60),
            (right_coupler_x + 4.56, 1.45),
            (right_coupler_x + 5.57, 1.30),
            (right_coupler_x + 6.33, 1.15),
            (right_coupler_x + 6.65, 1.00),
            (right_coupler_x + 6.74, 0.85),
            (right_coupler_x + 7.31, 0.70),
            (right_coupler_x + 8.04, 0.55),
            (right_coupler_x + 9.74, 0.40),
            (right_end_x, bottom_right_port_y),
        ]
    )
    points.append((active_length - taper_length, bottom_right_port_y))
    return points


def bottom_left_bend_points() -> list[tuple[float, float]]:
    bottom_coupler_y = top_coupler_y - coupling_gap - (top_width + bottom_width) / 2.0
    left_bend_start_x = 19.5
    return [
        (left_bend_start_x, bottom_left_port_y),
        (20.99 + bottom_left_bend_x_shift, 0.40),
        (23.27 + bottom_left_bend_x_shift, 0.55),
        (24.44 + bottom_left_bend_x_shift, 0.70),
        (25.04 + bottom_left_bend_x_shift, 0.85),
        (25.35 + bottom_left_bend_x_shift, 1.00),
        (25.48 + bottom_left_bend_x_shift, 1.15),
        (25.99 + bottom_left_bend_x_shift, 1.30),
        (26.97 + bottom_left_bend_x_shift, 1.45),
        (28.83 + bottom_left_bend_x_shift, 1.60),
        (left_coupler_x, bottom_coupler_y),
    ]


def bottom_right_bend_points() -> list[tuple[float, float]]:
    bottom_coupler_y = top_coupler_y - coupling_gap - (top_width + bottom_width) / 2.0
    right_coupler_x = left_coupler_x + coupling_length
    right_end_x = right_coupler_x + right_bend_length
    return [
        (right_coupler_x, bottom_coupler_y),
        (right_coupler_x + 2.00, 1.60),
        (right_coupler_x + 4.56, 1.45),
        (right_coupler_x + 5.57, 1.30),
        (right_coupler_x + 6.33, 1.15),
        (right_coupler_x + 6.65, 1.00),
        (right_coupler_x + 6.74, 0.85),
        (right_coupler_x + 7.31, 0.70),
        (right_coupler_x + 8.04, 0.55),
        (right_coupler_x + 9.74, 0.40),
        (right_end_x, bottom_right_port_y),
    ]


def add_bend_boost(
    component: gf.Component,
    points: list[tuple[float, float]],
    guide_width: float,
    bend_width: float,
    split_index: int,
) -> None:
    first = points[: split_index + 1]
    second = points[split_index:]
    component.add_ref(make_transition_segment(first, guide_width, bend_width))
    component.add_ref(make_transition_segment(second, bend_width, guide_width))


@gf.cell
def directional_coupler_recreation() -> gf.Component:
    component = gf.Component()
    top_points = top_route_points()
    bottom_points = bottom_route_points()
    active_length = active_footprint_length()

    component.add_ref(
        make_transition_segment(
            [(0.0, top_left_port_y), (taper_length, top_left_port_y)],
            top_port_tip_width,
            top_width,
        )
    )
    component.add_ref(make_route(top_points, top_width))
    add_bend_boost(component, top_left_bend_points(), top_width, top_left_bend_width, 4)
    add_bend_boost(component, top_right_bend_points(), top_width, top_right_bend_width, 5)
    component.add_ref(
        make_transition_segment(
            [(active_length - taper_length, top_right_port_y), (active_length, top_right_port_y)],
            top_width,
            top_port_tip_width,
        )
    )

    component.add_ref(
        make_transition_segment(
            [(0.0, bottom_left_port_y), (taper_length, bottom_left_port_y)],
            bottom_port_tip_width,
            bottom_width,
        )
    )
    component.add_ref(make_route(bottom_points, bottom_width))
    add_bend_boost(component, bottom_left_bend_points(), bottom_width, bottom_left_bend_width, 5)
    add_bend_boost(component, bottom_right_bend_points(), bottom_width, bottom_right_bend_width, 5)
    component.add_ref(
        make_transition_segment(
            [
                (active_length - taper_length, bottom_right_port_y),
                (active_length, bottom_right_port_y),
            ],
            bottom_width,
            bottom_port_tip_width,
        )
    )

    script_dir = Path(__file__).resolve().parent
    coupling_span_length = path_length(
        [(left_coupler_x, top_coupler_y), (left_coupler_x + coupling_length, top_coupler_y)]
    )
    reference_length = 0.0
    (script_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {
                    "coupling_span": coupling_span_length,
                    "reference": reference_length,
                },
                "delta_length_um": abs(coupling_span_length - reference_length),
            },
            indent=2,
        )
    )

    return component


if __name__ == "__main__":
    c = directional_coupler_recreation().copy()
    c.flatten()
    c.write_gds(Path(__file__).resolve().parent / gds_filename)
