from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


LAYER = (1, 0)

# Footprint and placement
footprint_length = 120.0
footprint_width = 4.0

# Function-defining optical knobs
wg_width_top = 0.35
wg_width_bottom = 0.28
access_bend_width_top = 0.70
access_bend_width_bottom = 0.58
coupling_gap = 0.155
coupling_length = 55.0
delta_length = 0.0

# Access geometry knobs
port_pitch = 3.46
coupled_pitch = 0.47
fanin_length = 32.0
fanout_length = 31.0
bend_radius = 5.7
left_stub = 10.0
right_stub = 11.0


def _bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    n: int = 80,
) -> list[tuple[float, float]]:
    t = np.linspace(0.0, 1.0, n)
    pts = (
        ((1 - t) ** 3)[:, None] * np.array(p0)
        + (3 * (1 - t) ** 2 * t)[:, None] * np.array(p1)
        + (3 * (1 - t) * t**2)[:, None] * np.array(p2)
        + (t**3)[:, None] * np.array(p3)
    )
    return [(float(x), float(y)) for x, y in pts]


def _path_from_points(points: list[tuple[float, float]]) -> gf.Path:
    deduped: list[tuple[float, float]] = []
    for point in points:
        if not deduped or point != deduped[-1]:
            deduped.append(point)
    return gf.Path(np.array(deduped, dtype=float))


def _add_guide(component: gf.Component, path: gf.Path, width: float) -> gf.ComponentReference:
    guide = path.extrude(width=width, layer=LAYER, simplify=0.002)
    return component << guide


@gf.cell
def directional_coupler_recreation() -> gf.Component:
    c = gf.Component()

    y_port_top = port_pitch / 2
    y_port_bottom = -port_pitch / 2
    y_c_top = coupled_pitch / 2
    y_c_bottom = -coupled_pitch / 2

    x_c0 = fanin_length
    x_c1 = x_c0 + coupling_length
    x_end = footprint_length

    top_left_bend = _bezier(
        (left_stub, y_port_top),
        (26.5, y_port_top),
        (26.5, y_c_top),
        (x_c0, y_c_top),
    )
    top_right_bend = _bezier(
        (x_c1, y_c_top),
        (93.0, y_c_top),
        (93.0, y_port_top),
        (x_end - right_stub, y_port_top),
    )
    bottom_left_bend = _bezier(
        (left_stub, y_port_bottom),
        (26.5, y_port_bottom),
        (26.5, y_c_bottom),
        (x_c0, y_c_bottom),
    )
    bottom_right_bend = _bezier(
        (x_c1, y_c_bottom),
        (93.0, y_c_bottom),
        (93.0, y_port_bottom),
        (x_end - right_stub, y_port_bottom),
    )

    top_points = (
        [(0.0, y_port_top), (left_stub, y_port_top)]
        + top_left_bend[1:]
        + [(x_c1, y_c_top)]
        + top_right_bend[1:]
        + [(x_end + delta_length, y_port_top)]
    )
    bottom_points = (
        [(0.0, y_port_bottom), (left_stub, y_port_bottom)]
        + bottom_left_bend[1:]
        + [(x_c1, y_c_bottom)]
        + bottom_right_bend[1:]
        + [(x_end, y_port_bottom)]
    )

    top_path = _path_from_points(top_points)
    bottom_path = _path_from_points(bottom_points)
    _add_guide(c, top_path, wg_width_top)
    _add_guide(c, bottom_path, wg_width_bottom)
    _add_guide(c, _path_from_points(top_left_bend), access_bend_width_top)
    _add_guide(c, _path_from_points(top_right_bend), access_bend_width_top)
    _add_guide(c, _path_from_points(bottom_left_bend), access_bend_width_bottom)
    _add_guide(c, _path_from_points(bottom_right_bend), access_bend_width_bottom)

    lengths = {
        "top": float(top_path.length()),
        "bottom": float(bottom_path.length()),
    }
    (Path(__file__).parent / "lengths.json").write_text(
        json.dumps(
            {
                "arms": lengths,
                "delta_length_um": abs(lengths["top"] - lengths["bottom"]),
            },
            indent=2,
        )
    )
    return c


if __name__ == "__main__":
    component = directional_coupler_recreation()
    component.write_gds(Path(__file__).with_suffix(".gds"), with_metadata=False)
