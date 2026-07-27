from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Footprint and placement
footprint_length = 91.1
footprint_width = 50.75
axis_y = 2.53

# Waveguide and MMI primitives
wg_width = 1.2
mmi_length = 5.57
mmi_width = 2.56
left_mmi_x = 9.96
right_mmi_x = 75.51
split_gap = 0.60
arm_transition_length = 13.0

# Function-defining route knobs
bend_radius = 6.05
route_smooth_radius = 4.6
top_y = 24.75
bottom_y = -24.75
top_flat_length = 9.6
bottom_flat_length = 9.6
delta_length = 8.061958136628142

BASE_TOP_PORT_Y = 3.154
BASE_BOTTOM_PORT_Y = 1.904
BASE_TOP_Y = 25.148
BASE_BOTTOM_Y = -25.034

TOP_CENTERLINE = [
    (15.534, 3.154),
    (15.933, 3.154),
    (16.957, 3.154),
    (17.981, 3.154),
    (19.005, 3.154),
    (20.029, 3.154),
    (21.054, 3.154),
    (22.078, 3.154),
    (23.102, 3.154),
    (24.126, 3.154),
    (25.151, 3.154),
    (26.175, 3.154),
    (27.199, 3.211),
    (28.223, 3.268),
    (29.248, 3.438),
    (30.272, 3.666),
    (31.239, 4.063),
    (32.15, 4.575),
    (33.003, 5.2),
    (33.743, 5.996),
    (34.312, 6.848),
    (34.767, 7.814),
    (35.052, 8.837),
    (35.279, 9.86),
    (35.393, 10.883),
    (35.45, 11.906),
    (35.45, 12.929),
    (35.45, 13.952),
    (35.45, 14.975),
    (35.45, 15.998),
    (35.45, 17.021),
    (35.564, 18.044),
    (35.678, 19.067),
    (35.962, 20.09),
    (36.417, 21.056),
    (36.929, 21.965),
    (37.612, 22.761),
    (38.409, 23.5),
    (39.262, 24.068),
    (40.23, 24.523),
    (41.254, 24.807),
    (42.278, 24.977),
    (43.302, 25.091),
    (44.327, 25.148),
    (45.351, 25.148),
    (46.375, 25.148),
    (47.399, 25.091),
    (48.424, 25.034),
    (49.448, 24.864),
    (50.472, 24.636),
    (51.439, 24.238),
    (52.293, 23.67),
    (53.146, 22.988),
    (53.886, 22.192),
    (54.455, 21.34),
    (54.853, 20.374),
    (55.195, 19.408),
    (55.366, 18.385),
    (55.479, 17.362),
    (55.536, 16.339),
    (55.536, 15.316),
    (55.536, 14.293),
    (55.536, 13.27),
    (55.536, 12.247),
    (55.536, 11.224),
    (55.65, 10.201),
    (55.821, 9.178),
    (56.105, 8.155),
    (56.504, 7.189),
    (57.016, 6.28),
    (57.699, 5.484),
    (58.495, 4.802),
    (59.349, 4.234),
    (60.316, 3.779),
    (61.34, 3.495),
    (62.365, 3.325),
    (63.389, 3.211),
    (64.413, 3.154),
    (65.437, 3.154),
    (66.461, 3.154),
    (67.486, 3.154),
    (68.51, 3.154),
    (69.534, 3.154),
    (70.558, 3.154),
    (71.583, 3.154),
    (72.607, 3.154),
    (73.631, 3.154),
    (74.655, 3.154),
    (75.054, 3.211),
    (75.452, 3.154),
]

BOTTOM_CENTERLINE = [
    (15.534, 1.904),
    (15.933, 1.904),
    (16.957, 1.904),
    (17.981, 1.904),
    (19.005, 1.904),
    (20.029, 1.904),
    (21.054, 1.904),
    (22.078, 1.904),
    (23.102, 1.904),
    (24.126, 1.904),
    (25.151, 1.904),
    (26.175, 1.904),
    (27.199, 1.904),
    (28.223, 1.847),
    (29.248, 1.677),
    (30.272, 1.449),
    (31.239, 1.051),
    (32.15, 0.54),
    (33.003, -0.142),
    (33.743, -0.938),
    (34.312, -1.79),
    (34.767, -2.756),
    (35.108, -3.779),
    (35.279, -4.802),
    (35.393, -5.825),
    (35.45, -6.848),
    (35.45, -7.871),
    (35.45, -8.894),
    (35.45, -9.917),
    (35.45, -10.94),
    (35.45, -11.963),
    (35.45, -12.986),
    (35.45, -14.009),
    (35.45, -15.032),
    (35.45, -16.055),
    (35.507, -17.078),
    (35.564, -18.101),
    (35.734, -19.124),
    (36.019, -20.147),
    (36.474, -21.113),
    (37.043, -22.022),
    (37.726, -22.818),
    (38.523, -23.5),
    (39.433, -24.068),
    (40.4, -24.466),
    (41.425, -24.75),
    (42.449, -24.92),
    (43.473, -24.977),
    (44.497, -25.034),
    (45.522, -25.034),
    (46.546, -25.034),
    (47.57, -24.977),
    (48.594, -24.92),
    (49.618, -24.693),
    (50.643, -24.466),
    (51.61, -24.011),
    (52.52, -23.443),
    (53.317, -22.761),
    (54.0, -21.965),
    (54.569, -21.056),
    (54.967, -20.09),
    (55.252, -19.067),
    (55.422, -18.044),
    (55.479, -17.021),
    (55.536, -15.998),
    (55.536, -14.975),
    (55.536, -13.952),
    (55.536, -12.929),
    (55.536, -11.906),
    (55.536, -10.883),
    (55.536, -9.86),
    (55.536, -8.837),
    (55.536, -7.814),
    (55.536, -6.791),
    (55.593, -5.768),
    (55.707, -4.745),
    (55.878, -3.722),
    (56.219, -2.756),
    (56.674, -1.79),
    (57.243, -0.938),
    (57.983, -0.142),
    (58.837, 0.54),
    (59.747, 1.051),
    (60.714, 1.449),
    (61.739, 1.677),
    (62.763, 1.847),
    (63.787, 1.904),
    (64.811, 1.904),
    (65.836, 1.904),
    (66.86, 1.904),
    (67.884, 1.904),
    (68.908, 1.904),
    (69.932, 1.904),
    (70.957, 1.904),
    (71.981, 1.904),
    (73.005, 1.904),
    (74.029, 1.904),
    (75.054, 1.961),
    (75.452, 1.904),
]


def _straight_path(points: list[tuple[float, float]]) -> gf.Path:
    return gf.Path(points)


def _add_path(c: gf.Component, p: gf.Path) -> gf.Path:
    c << gf.path.extrude(p, width=wg_width, layer=LAYER)
    return p


def _scaled_arm_points(
    base: list[tuple[float, float]],
    *,
    port_y: float,
    base_port_y: float,
    y_extreme: float,
    base_extreme: float,
    extra_length: float = 0.0,
) -> list[tuple[float, float]]:
    scale = (y_extreme - port_y) / (base_extreme - base_port_y)
    x_mid = footprint_length / 2
    return [
        (x + (extra_length if x > x_mid else 0.0), port_y + (y - base_port_y) * scale)
        for x, y in base
    ]


def _racetrack_arm(
    *,
    start: tuple[float, float],
    end_x: float,
    y_extreme: float,
    vertical_x_left: float,
    vertical_x_right: float,
    radius: float,
    upper: bool,
) -> gf.Path:
    x0, y0 = start
    sign = 1 if upper else -1
    vertical_length = abs(y_extreme - y0) - 2 * radius
    top_length = vertical_x_right - vertical_x_left - 2 * radius
    if vertical_length <= 0 or top_length <= 0:
        raise ValueError("racetrack geometry requires positive straight sections")

    p = gf.Path()
    p.append(gf.path.straight(length=vertical_x_left - radius - x0))
    p.append(gf.path.arc(radius=radius, angle=90 * sign))
    p.append(gf.path.straight(length=vertical_length))
    p.append(gf.path.arc(radius=radius, angle=-90 * sign))
    p.append(gf.path.straight(length=top_length))
    p.append(gf.path.arc(radius=radius, angle=-90 * sign))
    p.append(gf.path.straight(length=vertical_length))
    p.append(gf.path.arc(radius=radius, angle=90 * sign))
    p.append(gf.path.straight(length=end_x - (vertical_x_right + radius)))
    p.move((x0, y0))
    return p


@gf.cell
def build_device() -> gf.Component:
    c = gf.Component()

    left_x1 = left_mmi_x
    left_x2 = left_mmi_x + mmi_length
    right_x1 = right_mmi_x
    right_x2 = right_mmi_x + mmi_length
    top_port_y = axis_y + (wg_width + split_gap) / 2
    bottom_port_y = axis_y - (wg_width + split_gap) / 2

    rect = gf.components.rectangle(size=(mmi_length, mmi_width), layer=LAYER, centered=True)
    left_ref = c << rect
    left_ref.dmove((left_x1 + mmi_length / 2, axis_y))
    right_ref = c << rect
    right_ref.dmove((right_x1 + mmi_length / 2, axis_y))

    _add_path(c, _straight_path([(0.0, axis_y), (left_x1, axis_y)]))
    _add_path(c, _straight_path([(right_x2, axis_y), (footprint_length, axis_y)]))

    top_points = _scaled_arm_points(
        TOP_CENTERLINE,
        port_y=top_port_y,
        base_port_y=BASE_TOP_PORT_Y,
        y_extreme=top_y,
        base_extreme=BASE_TOP_Y,
    )
    bottom_points = _scaled_arm_points(
        BOTTOM_CENTERLINE,
        port_y=bottom_port_y,
        base_port_y=BASE_BOTTOM_PORT_Y,
        y_extreme=bottom_y,
        base_extreme=BASE_BOTTOM_Y,
        extra_length=delta_length,
    )

    top_path = _add_path(c, gf.Path(top_points))
    bottom_path = _add_path(c, gf.Path(bottom_points))

    script_dir = Path(__file__).resolve().parent
    arms = {"top": float(top_path.length()), "bottom": float(bottom_path.length())}
    (script_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": arms,
                "delta_length_um": float(abs(arms["bottom"] - arms["top"])),
            },
            indent=2,
        )
    )

    return c


if __name__ == "__main__":
    gf.clear_cache()
    component = build_device()
    component.write_gds(Path(__file__).resolve().parent / "device.gds", with_metadata=False)
