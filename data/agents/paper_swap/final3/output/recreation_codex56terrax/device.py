"""Primitives-only reconstruction of the final3 asymmetric directional coupler."""

from pathlib import Path
import json

import gdsfactory as gf
import numpy as np


# Top-level parametric contract: all optical-function dimensions are editable here.
wg_width = 0.29
port_separation = 3.45
s_bend_length = 19.0
s_bend_offset = 1.52
bend_radius = 3.0
interaction_length = 52.0
# The lower guide stays at the nominal transfer length while a retune of
# interaction_length lengthens the upper guide as a real phase/transfer bias.
# They are equal in the reconstructed nominal layout.
lower_interaction_length = 52.0
coupling_gap = 0.17
upper_width_start = 0.40
upper_width_end = 0.30
lower_width_start = 0.17
lower_width_end = 0.27
taper_length = 10.0

# Placement and sampling dimensions for this 120 x 4 um device frame.
layer = (1, 0)
device_length = 120.0
interaction_center_y = 1.9875
left_access_length = 15.0
curve_points = 161
left_upper_curve_width_boost = 0.82
right_upper_curve_width_boost = 0.95
left_lower_curve_width_boost = 0.58
right_lower_curve_width_boost = 0.75
left_upper_flare_center = 0.54
right_upper_flare_center = 0.46
left_lower_flare_center = 0.58
right_lower_flare_center = 0.50
left_upper_flare_sigma = 0.14
right_upper_flare_sigma = 0.11
left_lower_flare_sigma = 0.095
right_lower_flare_sigma = 0.12
upper_left_curve_center = 0.50
lower_left_curve_center = 0.55
right_curve_center = 0.45
output_port_skew = 0.215
upper_output_s_bend_offset = 1.615


def _cross_section(width: float) -> gf.CrossSection:
    """Single material section used for every route; no raw polygon emission."""
    return gf.CrossSection(
        sections=(
            gf.Section(
                width=width,
                layer=layer,
                name="wg",
                port_names=("o1", "o2"),
            ),
        )
    )


def _extrude(points: np.ndarray, width1: float, width2: float) -> gf.Component:
    """Extrude a centerline with a constant or linearly changing primitive width."""
    path = gf.Path(points)
    if abs(width1 - width2) < 1e-12:
        return path.extrude(cross_section=_cross_section(width1))
    transition = gf.path.transition(
        _cross_section(width1), _cross_section(width2), width_type="linear"
    )
    return path.extrude_transition(transition)


def _extrude_curve_bell(
    points: np.ndarray,
    base_width: float,
    width_boost: float,
    flare_center: float,
    flare_sigma: float,
) -> gf.Component:
    """Primitive Path extrusion with a smooth local multimode flare in an S bend."""
    def width_profile(t: np.ndarray) -> np.ndarray:
        return base_width + width_boost * np.exp(
            -((t - flare_center) / flare_sigma) ** 2
        )

    cross_section = gf.CrossSection(
        sections=(
            gf.Section(
                width=base_width,
                layer=layer,
                name="wg",
                port_names=("o1", "o2"),
                width_function=width_profile,
            ),
        )
    )
    return gf.Path(points).extrude(cross_section=cross_section)


def _s_curve(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    *,
    center: float,
    reverse: bool = False,
) -> np.ndarray:
    """Horizontal-tangent monotone S bend represented as a GDSFactory Path centerline."""
    t = np.linspace(0.0, 1.0, curve_points)
    if reverse:
        t = t[::-1]
    curve_exponent = 9.0 / bend_radius
    left = (t / center) ** curve_exponent
    right = ((1.0 - t) / (1.0 - center)) ** curve_exponent
    eased = left / (
        left + right + 1e-15
    )
    return np.column_stack((x0 + (x1 - x0) * t, y0 + (y1 - y0) * eased))


def _left_route(
    y_port: float,
    y_interaction: float,
    interaction_width: float,
    curve_width_boost: float,
    curve_center: float,
    flare_center: float,
    flare_sigma: float,
) -> list[tuple[np.ndarray, float, float, float, float, float]]:
    """Access straight, width transition, and approach S bend."""
    x_taper_start = left_access_length - taper_length
    x_interaction = left_access_length + s_bend_length
    lead = np.array([[0.0, y_port], [x_taper_start, y_port]])
    precurve = np.array([[x_taper_start, y_port], [left_access_length, y_port]])
    curve = _s_curve(
        left_access_length,
        y_port,
        x_interaction,
        y_interaction,
        center=curve_center,
    )
    return [
        (lead, wg_width, wg_width, 0.0, 0.0, 1.0),
        (precurve, wg_width, interaction_width, 0.0, 0.0, 1.0),
        (
            curve,
            interaction_width,
            interaction_width,
            curve_width_boost,
            flare_center,
            flare_sigma,
        ),
    ]


def _right_route(
    y_interaction: float,
    y_port: float,
    interaction_width: float,
    curve_width_boost: float,
    curve_center: float,
    flare_center: float,
    flare_sigma: float,
    interaction_end_x: float,
    device_end_x: float,
) -> list[tuple[np.ndarray, float, float, float, float, float]]:
    """Departure S bend, width transition, and access straight."""
    x_curve_end = interaction_end_x + s_bend_length
    x_taper_end = x_curve_end + taper_length
    curve = _s_curve(
        interaction_end_x,
        y_interaction,
        x_curve_end,
        y_port,
        center=curve_center,
    )
    postcurve = np.array([[x_curve_end, y_port], [x_taper_end, y_port]])
    lead = np.array([[x_taper_end, y_port], [device_end_x, y_port]])
    return [
        (
            curve,
            interaction_width,
            interaction_width,
            curve_width_boost,
            flare_center,
            flare_sigma,
        ),
        (postcurve, interaction_width, wg_width, 0.0, 0.0, 1.0),
        (lead, wg_width, wg_width, 0.0, 0.0, 1.0),
    ]


@gf.cell
def asymmetric_directional_coupler() -> gf.Component:
    """Two S-bent, oppositely tapered guides forming an adiabatic coupler."""
    c = gf.Component()
    x_left = left_access_length + s_bend_length
    x_right_upper = x_left + interaction_length
    x_right_lower = x_left + lower_interaction_length
    upper_device_end = device_length + interaction_length - lower_interaction_length

    separation_left = coupling_gap + (upper_width_start + lower_width_start) / 2.0
    separation_right = coupling_gap + (upper_width_end + lower_width_end) / 2.0
    upper_y_left = interaction_center_y + separation_left / 2.0
    lower_y_left = interaction_center_y - separation_left / 2.0
    upper_y_right = interaction_center_y + separation_right / 2.0
    lower_y_right = interaction_center_y - separation_right / 2.0

    upper_port_left = upper_y_left + s_bend_offset
    lower_port_left = upper_port_left - port_separation
    upper_port_right = upper_y_right + upper_output_s_bend_offset
    lower_port_right = upper_port_right - port_separation - output_port_skew

    upper_routes = [
        *_left_route(
            upper_port_left,
            upper_y_left,
            upper_width_start,
            left_upper_curve_width_boost,
            upper_left_curve_center,
            left_upper_flare_center,
            left_upper_flare_sigma,
        ),
        (
            np.array([[x_left, upper_y_left], [x_right_upper, upper_y_right]]),
            upper_width_start,
            upper_width_end,
            0.0,
            0.0,
            1.0,
        ),
        *_right_route(
            upper_y_right,
            upper_port_right,
            upper_width_end,
            right_upper_curve_width_boost,
            right_curve_center,
            right_upper_flare_center,
            right_upper_flare_sigma,
            x_right_upper,
            upper_device_end,
        ),
    ]
    lower_routes = [
        *_left_route(
            lower_port_left,
            lower_y_left,
            lower_width_start,
            left_lower_curve_width_boost,
            lower_left_curve_center,
            left_lower_flare_center,
            left_lower_flare_sigma,
        ),
        (
            np.array([[x_left, lower_y_left], [x_right_lower, lower_y_right]]),
            lower_width_start,
            lower_width_end,
            0.0,
            0.0,
            1.0,
        ),
        *_right_route(
            lower_y_right,
            lower_port_right,
            lower_width_end,
            right_lower_curve_width_boost,
            right_curve_center,
            right_lower_flare_center,
            right_lower_flare_sigma,
            x_right_lower,
            device_length,
        ),
    ]
    routes = upper_routes + lower_routes
    for points, width1, width2, width_boost, flare_center, flare_sigma in routes:
        if width_boost:
            c.add_ref(
                _extrude_curve_bell(
                    points, width1, width_boost, flare_center, flare_sigma
                )
            )
        else:
            c.add_ref(_extrude(points, width1, width2))

    upper_length = sum(gf.Path(points).length() for points, *_ in upper_routes)
    lower_length = sum(gf.Path(points).length() for points, *_ in lower_routes)
    Path(__file__).with_name("lengths.json").write_text(
        json.dumps(
            {
                "arms": {"upper": upper_length, "lower": lower_length},
                "delta_length_um": abs(upper_length - lower_length),
            },
            indent=2,
        )
    )
    return c


if __name__ == "__main__":
    asymmetric_directional_coupler().write_gds(
        Path(__file__).with_name("device.gds"), with_metadata=False
    )
