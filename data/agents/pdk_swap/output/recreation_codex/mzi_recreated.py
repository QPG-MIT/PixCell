from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


LAYER = (1, 0)

# Footprint and principal dimensions, in um.
footprint_length = 91.1
footprint_width = 50.75
axis_y = 2.63

# Waveguide and compact splitter/combiner parameters.
wg_width = 0.50
io_width = 0.44
io_taper_width = 1.0
splitter_width = 2.5
splitter_length = 5.45
splitter_x0 = 10.0
combiner_x0 = 75.65
port_separation = 1.27
split_taper_length = 13.1
splitter_port_width = 0.86

# Arm routing parameters.
left_arm_x = 28.55
left_vertical_x = 35.66
right_vertical_x = 55.66
right_arm_x = 62.55
top_margin = 0.0
top_inner_y = 11.2
top_outer_y = 18.75
top_flat_x0 = 42.55
top_flat_x1 = 48.55
curve_control_dx = 3.2
curve_control_dy = 3.0
corner_control_dx = 3.2
corner_control_dy = 2.6

# The lower arm is longer by this amount; the value perturbs real geometry.
delta_length = 10.5

ARM_LENGTHS: dict[str, float] = {}


def _rect(c: gf.Component, x0: float, y0: float, sx: float, sy: float) -> None:
    ref = c << gf.components.rectangle(size=(sx, sy), layer=LAYER, centered=False)
    ref.move((x0, y0))


def _taper(
    c: gf.Component,
    x0: float,
    y: float,
    length: float,
    width1: float,
    width2: float,
) -> None:
    ref = c << gf.components.taper(
        length=length,
        width1=width1,
        width2=width2,
        layer=LAYER,
        with_bbox=False,
    )
    ref.move((x0, y))


def _arm_paths() -> tuple[gf.Path, gf.Path]:
    upper_y = axis_y + port_separation / 2
    lower_y = axis_y - port_separation / 2
    top_y = footprint_width / 2 - top_margin - wg_width / 2

    top_rise = top_y - upper_y
    bottom_y = lower_y - top_rise - delta_length / 2

    bottom_inner_y = lower_y - (top_inner_y - upper_y)
    bottom_outer_y = bottom_y + (top_y - top_outer_y)

    def cubic(
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
        samples: int = 24,
    ) -> list[tuple[float, float]]:
        t = np.linspace(0.0, 1.0, samples)
        pts = (
            ((1 - t) ** 3)[:, None] * np.array(p0)
            + (3 * (1 - t) ** 2 * t)[:, None] * np.array(p1)
            + (3 * (1 - t) * t**2)[:, None] * np.array(p2)
            + (t**3)[:, None] * np.array(p3)
        )
        return [(float(x), float(y)) for x, y in pts]

    def extend(points: list[tuple[float, float]], new: list[tuple[float, float]]) -> None:
        points.extend(new[1:] if points else new)

    def routed_arm(start_y: float, inner_y: float, outer_y: float, extreme_y: float) -> gf.Path:
        downward = extreme_y < start_y
        sign = -1 if downward else 1
        points: list[tuple[float, float]] = []

        extend(
            points,
            cubic(
                (left_arm_x, start_y),
                (left_arm_x + curve_control_dx, start_y),
                (left_vertical_x, inner_y - sign * curve_control_dy),
                (left_vertical_x, inner_y),
            ),
        )
        points.append((left_vertical_x, outer_y))
        extend(
            points,
            cubic(
                (left_vertical_x, outer_y),
                (left_vertical_x, outer_y + sign * corner_control_dy),
                (top_flat_x0 - corner_control_dx, extreme_y),
                (top_flat_x0, extreme_y),
            ),
        )
        points.append((top_flat_x1, extreme_y))
        extend(
            points,
            cubic(
                (top_flat_x1, extreme_y),
                (top_flat_x1 + corner_control_dx, extreme_y),
                (right_vertical_x, outer_y + sign * corner_control_dy),
                (right_vertical_x, outer_y),
            ),
        )
        points.append((right_vertical_x, inner_y))
        extend(
            points,
            cubic(
                (right_vertical_x, inner_y),
                (right_vertical_x, inner_y - sign * curve_control_dy),
                (right_arm_x - curve_control_dx, start_y),
                (right_arm_x, start_y),
            ),
        )
        return gf.Path(points)

    top_path = routed_arm(upper_y, top_inner_y, top_outer_y, top_y)
    bottom_path = routed_arm(lower_y, bottom_inner_y, bottom_outer_y, bottom_y)
    return top_path, bottom_path


@gf.cell
def recreated_mzi() -> gf.Component:
    global ARM_LENGTHS

    c = gf.Component()
    upper_y = axis_y + port_separation / 2
    lower_y = axis_y - port_separation / 2

    _taper(c, 0.0, axis_y, splitter_x0, io_width, io_taper_width)
    _rect(
        c,
        splitter_x0,
        axis_y - splitter_width / 2,
        splitter_length,
        splitter_width,
    )

    splitter_x1 = splitter_x0 + splitter_length
    _taper(c, splitter_x1, upper_y, split_taper_length, splitter_port_width, wg_width)
    _taper(c, splitter_x1, lower_y, split_taper_length, splitter_port_width, wg_width)

    top_path, bottom_path = _arm_paths()
    ARM_LENGTHS = {
        "top": float(top_path.length()),
        "bottom": float(bottom_path.length()),
    }

    c << gf.path.extrude(top_path, layer=LAYER, width=wg_width)
    c << gf.path.extrude(bottom_path, layer=LAYER, width=wg_width)

    _taper(c, right_arm_x, upper_y, combiner_x0 - right_arm_x, wg_width, splitter_port_width)
    _taper(c, right_arm_x, lower_y, combiner_x0 - right_arm_x, wg_width, splitter_port_width)
    _rect(
        c,
        combiner_x0,
        axis_y - splitter_width / 2,
        splitter_length,
        splitter_width,
    )
    _taper(
        c,
        combiner_x0 + splitter_length,
        axis_y,
        footprint_length - combiner_x0 - splitter_length,
        io_taper_width,
        io_width,
    )

    c.add_port(
        "o1",
        center=(0.0, axis_y),
        width=io_width,
        orientation=180,
        layer=LAYER,
        port_type="optical",
    )
    c.add_port(
        "o2",
        center=(footprint_length, axis_y),
        width=io_width,
        orientation=0,
        layer=LAYER,
        port_type="optical",
    )
    return c


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    gds_path = out_dir / "mzi_recreated.gds"
    lengths_path = out_dir / "lengths.json"

    component = recreated_mzi()
    component.write_gds(gds_path, with_metadata=False)

    top_length = ARM_LENGTHS["top"]
    bottom_length = ARM_LENGTHS["bottom"]
    payload = {
        "arms": ARM_LENGTHS,
        "delta_length_um": abs(bottom_length - top_length),
    }
    lengths_path.write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
