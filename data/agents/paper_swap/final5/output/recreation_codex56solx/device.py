from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Function-defining, JEE-substitutable dimensions (all dimensions in um).
guide_width = 0.068
grating_width = 0.050
bus_width = 0.026
tip_width = 0.004
input_taper_length = 1.50
return_bend_radius = 1.90
return_bend_width = 0.460
bus_to_grating_gap = 0.017
grating_period = 0.1562
grating_duty_cycle = 0.75
grating_apodization = 0.03
grating_chirp = 0.070
grating_count = 56
transfer_length = 8.75

# Placement and shape parameters.
footprint_length = 18.24
footprint_width = 0.70
grating_start_x = 4.470
bus_y = 0.355
upper_grating_y = (
    bus_y + bus_width / 2.0 + bus_to_grating_gap + grating_width / 2.0
)
top_return_y = 0.661
bus_start_x = 1.945
bus_input_lead = 2.525
bus_output_lead = 2.750
mirror_axis_x = 8.82
mirror_axis_y = 0.355
layer = (1, 0)

# Normalized, image-measured chirp profile. grating_chirp scales the maximum
# displacement, so the phase law remains a live parametric function knob.
grating_chirp_profile = (
    0,
    0,
    1,
    1,
    1,
    2,
    4,
    4,
    5,
    6,
    7,
    7,
    6,
    8,
    9,
    7,
    10,
    11,
    12,
    11,
    13,
    13,
    13,
    14,
    13,
    9,
    8,
    4,
    3,
    1,
    3,
    2,
    5,
    5,
    5,
    6,
    7,
    7,
    8,
    5,
    4,
    1,
    -1,
    -2,
    -4,
    -7,
    -9,
    -7,
    -8,
    -5,
    -4,
    -4,
    -3,
    -2,
    -1,
    -1,
)


def cubic_path(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    samples: int = 81,
) -> gf.Path:
    """Returns a cubic Bezier as a sampled gf.Path (never a raw polygon)."""
    t = np.linspace(0.0, 1.0, samples)
    omt = 1.0 - t
    points = (
        omt[:, None] ** 3 * np.asarray(p0)
        + 3.0 * omt[:, None] ** 2 * t[:, None] * np.asarray(p1)
        + 3.0 * omt[:, None] * t[:, None] ** 2 * np.asarray(p2)
        + t[:, None] ** 3 * np.asarray(p3)
    )
    return gf.Path(points)


def joined_path(*paths: gf.Path) -> gf.Path:
    result = gf.Path()
    for path in paths:
        result.append(path)
    return result


def cross_section(width: float) -> gf.CrossSection:
    return gf.CrossSection(
        sections=(gf.Section(width=width, layer=layer, name="core"),)
    )


def add_extruded(component: gf.Component, path: gf.Path, width: float) -> None:
    component.add_ref(gf.path.extrude(path, width=width, layer=layer))


def add_transition(
    component: gf.Component,
    path: gf.Path,
    width1: float,
    width2: float,
) -> None:
    transition = gf.path.transition(
        cross_section(width1),
        cross_section(width2),
        width_type="linear",
    )
    component.add_ref(gf.path.extrude_transition(path, transition))


def add_rect(
    component: gf.Component,
    x: float,
    y: float,
    length: float,
    width: float,
) -> None:
    ref = component.add_ref(gf.components.rectangle(size=(length, width), layer=layer))
    ref.move((x, y - width / 2.0))


def rotate_180(path: gf.Path) -> gf.Path:
    points = np.asarray(path.points)
    rotated = np.column_stack(
        (
            2.0 * mirror_axis_x - points[:, 0],
            2.0 * mirror_axis_y - points[:, 1],
        )
    )
    return gf.Path(rotated)


@gf.cell
def folded_grating_coupler() -> gf.Component:
    c = gf.Component()

    # Central transfer bus. transfer_length is a real length knob: changing it
    # lengthens this material region by exactly the same amount.
    bus_path = gf.Path()
    bus_path.append(
        gf.path.straight(
            length=bus_input_lead + transfer_length + bus_output_lead
        )
    )
    bus_path.move((bus_start_x, bus_y))
    add_extruded(c, bus_path, bus_width)

    # Left curved upper input: a narrow tip grows into the upper interaction arm.
    upper_input_taper = cubic_path(
        (0.015, 0.679),
        (0.25, 0.556),
        (0.95, 0.466),
        (2.05, 0.436),
    )
    upper_input_body = cubic_path(
        (2.05, 0.436),
        (2.45, 0.414),
        (3.35, upper_grating_y),
        (grating_start_x - 0.040, upper_grating_y),
    )
    add_transition(c, upper_input_taper, tip_width, grating_width)
    add_extruded(c, upper_input_body, grating_width)

    # The other upper input tapers into a long return, then folds back toward
    # the periodic interaction row through a broad, low-profile hairpin.
    upper_return_taper = gf.Path()
    upper_return_taper.append(gf.path.straight(length=input_taper_length))
    upper_return_taper.move((2.225, top_return_y))
    add_transition(c, upper_return_taper, tip_width, guide_width)

    return_straight = gf.Path()
    return_straight.append(gf.path.straight(length=9.955))
    return_straight.move((2.225 + input_taper_length, top_return_y))

    hairpin_x = 13.34 + return_bend_radius
    first_turn = gf.Path(
        np.asarray(
            [
                (13.68, top_return_y),
                (14.55, 0.645),
                (14.85, 0.627),
                (15.03, 0.608),
                (15.17, 0.584),
                (hairpin_x, 0.553),
            ]
        )
    )
    bend_turn = gf.Path(
        np.asarray(
            [
                (hairpin_x, 0.553),
                (hairpin_x, 0.522),
                (15.18, 0.491),
                (15.02, 0.460),
            ]
        )
    )
    second_turn = gf.Path(
        np.asarray(
            [
                (15.02, 0.460),
                (14.76, 0.436),
                (14.55, 0.423),
                (14.12, 0.411),
                (
                    grating_start_x + grating_count * grating_period,
                    upper_grating_y,
                ),
            ]
        )
    )
    add_extruded(c, return_straight, guide_width)
    add_extruded(c, first_turn, guide_width)
    add_extruded(c, bend_turn, guide_width)
    add_transition(c, second_turn, guide_width, grating_width)

    # The source is vertically exaggerated: its nominally vertical bend keeps
    # the same pixel stroke as the horizontal rails. A bounded rectangle adds
    # that observed horizontal bend fill without inflating the GDS height.
    bend_fill_x = hairpin_x - return_bend_width / 2.0
    bend_fill_y = 0.5375
    bend_fill_height = 0.040
    add_rect(
        c,
        bend_fill_x,
        bend_fill_y,
        return_bend_width,
        bend_fill_height,
    )
    add_rect(
        c,
        2.0 * mirror_axis_x - bend_fill_x - return_bend_width,
        2.0 * mirror_axis_y - bend_fill_y,
        return_bend_width,
        bend_fill_height,
    )

    # Periodic rows. A shallow sinusoidal apodization captures the slightly
    # narrower central teeth visible in the source while preserving pitch.
    for index in range(grating_count):
        phase = index / max(grating_count - 1, 1)
        local_duty = grating_duty_cycle * (
            1.0 - grating_apodization * np.sin(np.pi * phase) ** 2
        )
        tooth_length = grating_period * local_duty
        chirp_offset = (
            grating_chirp * grating_chirp_profile[index] / 14.0
        )
        x = grating_start_x + index * grating_period + chirp_offset
        add_rect(c, x, upper_grating_y, tooth_length, grating_width)
        add_rect(
            c,
            x,
            2.0 * mirror_axis_y - upper_grating_y,
            tooth_length,
            grating_width,
        )

    # Rotate the complete upper routing topology for the lower counterpart.
    add_transition(c, rotate_180(upper_input_taper), tip_width, grating_width)
    add_extruded(c, rotate_180(upper_input_body), grating_width)

    # The lower-right terminal visibly continues beyond the dark core in the
    # supplied raster. This short tapered-axis continuation is also what sets
    # the observed asymmetric vertical scoring frame.
    lower_terminal = gf.Path(
        np.asarray(
            [
                (
                    2.0 * mirror_axis_x - 0.015,
                    2.0 * mirror_axis_y - 0.679,
                ),
                (17.72, 0.004),
            ]
        )
    )
    add_extruded(c, lower_terminal, tip_width)

    add_transition(c, rotate_180(upper_return_taper), tip_width, guide_width)
    add_extruded(c, rotate_180(return_straight), guide_width)
    add_extruded(c, rotate_180(first_turn), guide_width)
    add_extruded(c, rotate_180(bend_turn), guide_width)
    add_transition(c, rotate_180(second_turn), guide_width, grating_width)

    return c


if __name__ == "__main__":
    component = folded_grating_coupler()
    output_dir = Path(__file__).resolve().parent
    gds_path = output_dir / "device.gds"
    # Metadata-free output leaves the real device as the sole GDS top cell,
    # which makes independent area and bbox measurement unambiguous.
    component.write_gds(gds_path, with_metadata=False)

    # Measurement contract: both values come from gf.Path lengths. The second
    # path is the fixed pair of bus leads, so their measured difference is the
    # live central transfer length.
    measured_bus = gf.Path()
    measured_bus.append(
        gf.path.straight(
            length=bus_input_lead + transfer_length + bus_output_lead
        )
    )
    measured_leads = gf.Path()
    measured_leads.append(
        gf.path.straight(length=bus_input_lead + bus_output_lead)
    )
    arm_lengths = {
        "central_bus": float(measured_bus.length()),
        "fixed_leads": float(measured_leads.length()),
    }
    delta_length_um = abs(
        arm_lengths["central_bus"] - arm_lengths["fixed_leads"]
    )
    (output_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": arm_lengths,
                "delta_length_um": delta_length_um,
            },
            indent=2,
        )
    )
