"""Primitive-only recreation of the three-core tapered mode-evolution device."""

import json

import gdsfactory as gf
import numpy as np


layer = (1, 0)

# Function-defining geometry knobs (all dimensions are in micrometres).
delta_length = 3.044554455  # center launch / transfer lead before the inverse taper
center_input_width_um = 0.26700
center_taper_length_um = 22.00495
center_tip_width_um = 0.07160
side_start_x_um = 3.044554455
side_tip_width_um = 0.06835
side_guide_width_um = 0.24100
side_taper_length_um = 22.00495
side_gap_um = 0.09415
output_lead_length_um = 4.00000
fanout_length_um = 10.95000
bend_radius_um = 1.50000
upper_start_y_um = 0.28140
lower_start_y_um = -0.26220
upper_taper_end_y_um = 0.27840
lower_taper_end_y_um = -0.25080
upper_output_y_um = 0.72900
lower_output_y_um = -0.72800
center_y_um = 0.01630


def _no_port_profile(width_um, width_function):
    return gf.cross_section.strip_no_ports(width=width_um, layer=layer).copy(
        width_function=width_function
    )


def _center_core():
    center_path_length_um = delta_length + center_taper_length_um
    center_path = gf.path.straight(length=center_path_length_um, npoints=128)

    def width_function(t):
        distance_um = t * center_path_length_um
        taper_fraction = np.clip(
            (distance_um - delta_length) / center_taper_length_um, 0.0, 1.0
        )
        return np.where(
            distance_um <= delta_length,
            center_input_width_um,
            center_input_width_um
            + (center_tip_width_um - center_input_width_um) * taper_fraction,
        )

    core = center_path.extrude(
        cross_section=_no_port_profile(center_input_width_um, width_function)
    )
    core.move(origin=(0, 0), destination=(0, center_y_um))
    return core, center_path


def _side_core(start_y_um, taper_end_y_um, output_y_um, gap_sign, curve_fractions):
    start_y_um = start_y_um + gap_sign * (side_gap_um - 0.09415)
    taper_end_x_um = side_start_x_um + side_taper_length_um
    bend_end_x_um = side_start_x_um + side_taper_length_um + fanout_length_um
    end_x_um = bend_end_x_um + output_lead_length_um
    points = [
        (side_start_x_um, start_y_um),
        (taper_end_x_um, taper_end_y_um),
        (taper_end_x_um + 1.90, taper_end_y_um),
        (
            taper_end_x_um + 3.45,
            taper_end_y_um + (output_y_um - taper_end_y_um) * curve_fractions[0],
        ),
        (
            taper_end_x_um + 4.65,
            taper_end_y_um + (output_y_um - taper_end_y_um) * curve_fractions[1],
        ),
        (
            taper_end_x_um + 7.13,
            taper_end_y_um + (output_y_um - taper_end_y_um) * curve_fractions[2],
        ),
        (
            taper_end_x_um + 9.60,
            taper_end_y_um + (output_y_um - taper_end_y_um) * curve_fractions[3],
        ),
        (bend_end_x_um, output_y_um),
        (end_x_um, output_y_um),
    ]
    path = gf.path.smooth(points, radius=bend_radius_um * 0.30)
    path_length_um = path.length()

    def width_function(t):
        distance_um = t * path_length_um
        taper_fraction = np.clip(distance_um / side_taper_length_um, 0.0, 1.0)
        return side_tip_width_um + (side_guide_width_um - side_tip_width_um) * taper_fraction

    core = path.extrude(
        cross_section=_no_port_profile(side_tip_width_um, width_function)
    )
    return core, path


@gf.cell
def device():
    component = gf.Component()
    center_core, center_path = _center_core()
    upper_core, upper_path = _side_core(
        upper_start_y_um,
        upper_taper_end_y_um,
        upper_output_y_um,
        1.0,
        (0.125, 0.288, 0.732, 0.972),
    )
    lower_core, lower_path = _side_core(
        lower_start_y_um,
        lower_taper_end_y_um,
        lower_output_y_um,
        -1.0,
        (0.125, 0.275, 0.700, 0.950),
    )
    component.add_ref(center_core)
    component.add_ref(upper_core)
    component.add_ref(lower_core)

    # Keep the measurement contract derived from path objects, not hand-entered.
    reference_path = gf.path.straight(length=center_taper_length_um)
    center_length_um = center_path.length()
    reference_length_um = reference_path.length()
    with open("lengths.json", "w", encoding="utf-8") as handle:
        json.dump(
            {
                "arms": {
                    "center": center_length_um,
                    "reference": reference_length_um,
                },
                "delta_length_um": abs(center_length_um - reference_length_um),
                "side_paths": {
                    "upper_um": upper_path.length(),
                    "lower_um": lower_path.length(),
                },
            },
            handle,
            indent=2,
        )
    component.flatten()
    return component


component = device()
component.write_gds("device.gds", with_metadata=False)
