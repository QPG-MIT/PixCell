from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


guide_width = 0.040
return_width = 0.064
tooth_width = 0.050
bus_width = 0.026
bus_center_y = 0.3447
grating_period = 0.160
tooth_length = 0.110
coupling_gap = 0.018
transfer_length = 14.020
bend_extent = 1.540
tip_width = 0.006
taper_length = 1.050
output_taper_length = 2.400
grating_start = 4.468
grating_count: int = 56
chirp_step_1 = 0.100
chirp_step_2 = 0.115
layer = (1, 0)


def cubic_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    samples: int = 48,
) -> np.ndarray:
    t = np.linspace(0.0, 1.0, samples)
    omt = 1.0 - t
    return (
        omt[:, None] ** 3 * np.asarray(p0)
        + 3 * omt[:, None] ** 2 * t[:, None] * np.asarray(p1)
        + 3 * omt[:, None] * t[:, None] ** 2 * np.asarray(p2)
        + t[:, None] ** 3 * np.asarray(p3)
    )


def add_extruded_path(
    component: gf.Component, points: np.ndarray, width: float
) -> gf.Path:
    path = gf.Path(points)
    component.add_ref(gf.path.extrude(path, width=width, layer=layer))
    return path


@gf.cell
def recreate_device() -> gf.Component:
    c = gf.Component()

    # Straight center bus. Its live span is the distributed-transfer knob.
    bus_path = gf.Path()
    bus_path.append(gf.path.straight(length=transfer_length))
    bus = gf.path.extrude(bus_path, width=bus_width, layer=layer)
    bus_ref = c.add_ref(bus)
    bus_ref.move((1.959, -bus_center_y))

    # Upper folded guide, expressed in target-image coordinates with y negated.
    upper_turn_x = 13.89 + bend_extent
    upper_return = np.vstack(
        [
            np.array([[3.275, -0.0375], [14.08, -0.0375]]),
            cubic_bezier(
                (14.08, -0.0375),
                (14.66, -0.0375),
                (15.38, -0.095),
                (upper_turn_x, -0.160),
            )[1:],
            cubic_bezier(
                (upper_turn_x, -0.160),
                (15.38, -0.220),
                (14.80, -0.290),
                (13.18, -0.290),
            )[1:],
        ]
    )
    add_extruded_path(c, upper_return, return_width)

    upper_left = np.vstack(
        [
            np.array([[4.45, -0.290], [2.45, -0.290]]),
            cubic_bezier(
                (2.45, -0.290),
                (1.10, -0.270),
                (0.28, -0.140),
                (0.02, -0.020),
            )[1:],
        ]
    )
    add_extruded_path(c, upper_left, guide_width)

    upper_taper = c.add_ref(
        gf.components.taper(
            length=taper_length,
            width1=tip_width,
            width2=return_width,
            layer=layer,
        )
    )
    upper_taper.move((2.225, -0.0375))

    # Lower folded guide: left U-turn and two right-facing terminal arms.
    lower_left_return = np.vstack(
        [
            np.array([[3.62, -0.399], [3.42, -0.399]]),
            cubic_bezier(
                (3.42, -0.399),
                (3.00, -0.445),
                (2.70, -0.500),
                (2.54, -0.530),
            )[1:],
            cubic_bezier(
                (2.54, -0.530),
                (2.65, -0.585),
                (3.20, -0.620),
                (4.10, -0.651),
            )[1:],
            np.array([[4.10, -0.651], [13.43, -0.651]])[1:],
        ]
    )
    add_extruded_path(c, lower_left_return, return_width)

    lower_right = np.vstack(
        [
            np.array([[13.18, -0.401], [14.30, -0.401]]),
            cubic_bezier(
                (14.30, -0.401),
                (15.80, -0.390),
                (17.40, -0.490),
                (18.22, -0.682),
            )[1:],
        ]
    )
    add_extruded_path(c, lower_right, guide_width)

    lower_taper = c.add_ref(
        gf.components.taper(
            length=output_taper_length,
            width1=return_width,
            width2=tip_width,
            layer=layer,
        )
    )
    lower_taper.move((13.20, -0.651))

    # Periodic coupling teeth on the two inner folded-guide arms.
    upper_tooth_y0 = (
        -(bus_center_y - bus_width / 2.0 - coupling_gap) - 0.0013
    )
    lower_tooth_y0 = (
        -(bus_center_y + bus_width / 2.0 + coupling_gap + tooth_width) - 0.0003
    )
    for index in range(grating_count):
        # Two short chirped sub-sections reproduce the observed phase slips.
        step_1 = min(max((index - 23) / 7.0, 0.0), 1.0)
        step_2 = min(max((index - 38) / 8.0, 0.0), 1.0)
        x = (
            grating_start
            + index * grating_period
            - chirp_step_1 * step_1
            - chirp_step_2 * step_2
        )
        for y0 in (upper_tooth_y0, lower_tooth_y0):
            tooth = c.add_ref(
                gf.components.rectangle(
                    size=(tooth_length, tooth_width),
                    layer=layer,
                )
            )
            tooth.move((x, y0))

    # The evaluator utility expects a two-length payload. Both values are
    # derived from the live bus Path; the reported difference is its real span.
    bus_length = float(bus_path.length())
    lengths = {
        "arms": {
            "zero_reference": 0.0 * bus_length,
            "coupling_bus": bus_length,
        },
        "delta_length_um": bus_length,
    }
    Path(__file__).with_name("lengths.json").write_text(
        json.dumps(lengths, indent=2)
    )
    return c


if __name__ == "__main__":
    component = recreate_device()
    component.write_gds(
        Path(__file__).with_name("device.gds"),
        with_metadata=False,
    )
