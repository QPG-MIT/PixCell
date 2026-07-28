from pathlib import Path
import json
import math

import gdsfactory as gf
import numpy as np


layer = (1, 0)

# Function-defining, top-level tunables (microns).
ring_radius = 1.24
ring_straight_length = 2.50
wg_width = 0.52
bend_width = 0.31
coupling_gap = 0.00
coupler_rail_width = 1.03
coupler_length = 0.89
lower_coupler_length = 0.89
access_block_edge = 0.445
slot_length = 0.33
slot_width = 0.54
slot_pitch = 0.44
transition_length = 0.34
access_width = 0.43
coupler_offset = 0.92


def capsule_centerline(radius: float, straight_length: float) -> gf.Path:
    """Closed fourth-order superelliptic racetrack centerline."""
    vertical_radius = radius + straight_length / 2
    exponent = 4.0
    theta = np.linspace(0, 2 * math.pi, 401)
    cos_t = np.cos(theta)
    sin_t = np.sin(theta)
    points = np.column_stack(
        (
            radius * np.sign(cos_t) * np.abs(cos_t) ** (2 / exponent),
            vertical_radius
            * np.sign(sin_t)
            * np.abs(sin_t) ** (2 / exponent),
        )
    )
    return gf.Path(points)


def tapered_racetrack() -> gf.Component:
    """Eight primitive path transitions, wide on flats and narrow in bends."""
    c = gf.Component()
    full_path = capsule_centerline(ring_radius, ring_straight_length)
    points = full_path.points
    samples_per_octant = (len(points) - 1) // 8
    widths = [
        wg_width,
        bend_width,
        wg_width,
        bend_width,
        wg_width,
        bend_width,
        wg_width,
        bend_width,
        wg_width,
    ]
    for index in range(8):
        start = index * samples_per_octant
        stop = (index + 1) * samples_per_octant
        segment = gf.Path(points[start : stop + 1])
        xs_start = gf.cross_section.cross_section(width=widths[index], layer=layer)
        xs_stop = gf.cross_section.cross_section(width=widths[index + 1], layer=layer)
        transition = gf.path.transition(xs_start, xs_stop, width_type="sine")
        c << gf.path.extrude_transition(segment, transition)
    return c


def slotted_rail(y: float, rail_length: float) -> tuple[gf.Component, gf.Path]:
    """Central wide rail with two primitive rectangular etched slots."""
    centerline = gf.Path([(-rail_length / 2, y), (rail_length / 2, y)])
    solid = gf.path.extrude(centerline, width=coupler_rail_width, layer=layer)

    cuts = gf.Component()
    for x in (-slot_pitch / 2, slot_pitch / 2):
        cut = cuts << gf.components.rectangle(
            size=(slot_length, slot_width), layer=layer
        )
        cut.center = (x, y)
    rail = gf.boolean(A=solid, B=cuts, operation="not", layer=layer)
    return rail, centerline


def access_path(points: list[tuple[float, float]]) -> gf.Component:
    return gf.path.extrude(gf.Path(points), width=access_width, layer=layer)


@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    c << tapered_racetrack()

    rail_top, _ = slotted_rail(coupler_offset, coupler_length)
    rail_bottom, _ = slotted_rail(-coupler_offset, lower_coupler_length)
    c << rail_top
    c << rail_bottom

    x_block = access_block_edge
    x_knee = x_block + transition_length
    x_side = ring_radius - wg_width / 2 - coupling_gap
    y_side = coupler_offset - 0.47

    c << access_path([(-x_block, coupler_offset), (-x_knee, coupler_offset), (-x_side, y_side)])
    c << access_path([(x_block, coupler_offset), (x_knee, coupler_offset), (x_side, y_side)])
    c << access_path([(-x_block, -coupler_offset), (-x_knee, -coupler_offset), (-x_side, -y_side)])
    c << access_path([(x_block, -coupler_offset), (x_knee, -coupler_offset), (x_side, -y_side)])
    return c


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    component = device()
    component.write_gds(output_dir / "device.gds", with_metadata=False)

    # Derived from the actual centerline used to form the central coupling rail.
    measured_coupler_path = gf.Path(
        [(-coupler_length / 2, coupler_offset), (coupler_length / 2, coupler_offset)]
    )
    measured_lower_path = gf.Path(
        [
            (-lower_coupler_length / 2, -coupler_offset),
            (lower_coupler_length / 2, -coupler_offset),
        ]
    )
    top_length = measured_coupler_path.length()
    lower_length = measured_lower_path.length()
    (output_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {
                    "upper_coupler_centerline": top_length,
                    "lower_coupler_centerline": lower_length,
                },
                "delta_length_um": abs(top_length - lower_length),
            },
            indent=2,
        )
        + "\n"
    )
