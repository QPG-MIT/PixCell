from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf


layer = (1, 0)

footprint_length = 40.0
footprint_width = 1.7

input_width = 0.268
input_straight_length = 3.05
central_taper_length = 22.05
central_tip_width = 0.070
central_y = 0.866

branch_tip_width = 0.068
branch_taper_length = 22.65
branch_start_x = 3.05
upper_branch_y = 1.131
lower_branch_y = 0.591
output_width = 0.242

bend_length = 9.75
upper_output_y = 1.579
lower_output_y = 0.121
output_straight_length = 4.55

delta_length = 0.0

samples: int = 80


def _smooth_s_points(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    straight: float,
    extra_straight: float = 0.0,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for i in range(samples + 1):
        t = i / samples
        s = 0.5 - 0.5 * math.cos(math.pi * t)
        points.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * s))
    points.append((x1 + straight + extra_straight, y1))
    return points


def _path_length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(x1 - x0, y1 - y0)
        for (x0, y0), (x1, y1) in zip(points[:-1], points[1:])
    )


@gf.cell
def splitter_trident() -> gf.Component:
    c = gf.Component()

    central_straight_path = gf.Path(
        [(0.0, central_y), (input_straight_length, central_y)]
    )
    c << gf.path.extrude(central_straight_path, width=input_width, layer=layer)

    central_taper = c << gf.components.taper(
        length=central_taper_length,
        width1=input_width,
        width2=central_tip_width,
        layer=layer,
        with_bbox=False,
    )
    central_taper.move((input_straight_length, central_y))

    upper_taper = c << gf.components.taper(
        length=branch_taper_length,
        width1=branch_tip_width,
        width2=output_width,
        layer=layer,
        with_bbox=False,
    )
    upper_taper.move((branch_start_x, upper_branch_y))

    lower_taper = c << gf.components.taper(
        length=branch_taper_length,
        width1=branch_tip_width,
        width2=output_width,
        layer=layer,
        with_bbox=False,
    )
    lower_taper.move((branch_start_x, lower_branch_y))

    bend_start_x = branch_start_x + branch_taper_length
    bend_end_x = bend_start_x + bend_length

    upper_points = _smooth_s_points(
        bend_start_x,
        upper_branch_y,
        bend_end_x,
        upper_output_y,
        output_straight_length,
        delta_length,
    )
    lower_points = _smooth_s_points(
        bend_start_x,
        lower_branch_y,
        bend_end_x,
        lower_output_y,
        output_straight_length,
    )
    c << gf.path.extrude(gf.Path(upper_points), width=output_width, layer=layer)
    c << gf.path.extrude(gf.Path(lower_points), width=output_width, layer=layer)

    return c


def write_lengths(script_path: Path) -> None:
    bend_start_x = branch_start_x + branch_taper_length
    bend_end_x = bend_start_x + bend_length
    upper_points = _smooth_s_points(
        bend_start_x,
        upper_branch_y,
        bend_end_x,
        upper_output_y,
        output_straight_length,
        delta_length,
    )
    lower_points = _smooth_s_points(
        bend_start_x,
        lower_branch_y,
        bend_end_x,
        lower_output_y,
        output_straight_length,
    )
    upper_len = branch_taper_length + _path_length(upper_points)
    lower_len = branch_taper_length + _path_length(lower_points)
    payload = {
        "arms": {
            "upper": upper_len,
            "lower": lower_len,
        },
        "delta_length_um": abs(upper_len - lower_len),
    }
    (script_path.parent / "lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    gf.clear_cache()
    here = Path(__file__).resolve()
    component = splitter_trident().copy()
    component.flatten()
    component.write_gds(here.parent / "device.gds")
    write_lengths(here)
