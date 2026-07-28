from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Layer and lithographic dimensions (um).
layer = (1, 0)
guide_width = 0.29
wide_tip_width = 0.40
narrow_tip_width = 0.18
gap = 0.17

# Function-defining adiabatic-coupler dimensions (um).
transfer_length = 54.0
taper_length = 54.0
left_transition_length = 16.5
right_transition_length = 14.0
left_lead_length = 17.0
right_lead_length = 18.5
left_top_bend_width = 1.04
left_bottom_bend_width = 0.37
right_top_bend_width = 0.85
right_bottom_bend_width = 0.75

# Port and interaction-region placement (um).
input_port_separation = 3.45
output_port_separation = 3.67
input_center_offset = 0.012
coupling_center_offset = -0.010
output_center_offset = 0.0

# Geometric discretization for the analytic S-bend centerlines.
curve_samples = 161


def _cross_section(width: float) -> gf.CrossSection:
    """Single primitive strip section on the required drawing layer."""
    section = gf.Section(
        width=width,
        layer=layer,
        name="core",
        port_names=("o1", "o2"),
    )
    return gf.CrossSection(sections=(section,))


def _cosine_path_halves(
    x_start: float,
    x_stop: float,
    y_start: float,
    y_stop: float,
) -> tuple[gf.Path, gf.Path]:
    """Cosine S-transition with horizontal tangents at both ends."""
    u = np.linspace(0.0, 1.0, curve_samples)
    x = x_start + (x_stop - x_start) * u
    progress = 0.5 - 0.5 * np.cos(np.pi * u)
    y = y_start + (y_stop - y_start) * progress
    points = np.column_stack((x, y))
    midpoint = curve_samples // 2
    return gf.Path(points[: midpoint + 1]), gf.Path(points[midpoint:])


def _straight_path(
    x_start: float,
    x_stop: float,
    y: float,
) -> gf.Path:
    return gf.Path([(x_start, y), (x_stop, y)])


def _extrude_constant(path: gf.Path, width: float) -> gf.Component:
    return path.extrude(cross_section=_cross_section(width))


def _extrude_linear(path: gf.Path, width_start: float, width_stop: float) -> gf.Component:
    transition = gf.path.transition(
        _cross_section(width_start),
        _cross_section(width_stop),
        width_type="linear",
    )
    return gf.path.extrude_transition(path, transition)


@gf.cell
def adiabatic_directional_coupler() -> gf.Component:
    """Primitive-only asymmetric adiabatic directional coupler."""
    component = gf.Component()

    interaction_x0 = left_lead_length + left_transition_length
    interaction_x1 = interaction_x0 + transfer_length
    output_transition_x1 = interaction_x1 + right_transition_length
    output_x1 = output_transition_x1 + right_lead_length

    input_top_y = input_center_offset + input_port_separation / 2.0
    input_bottom_y = input_center_offset - input_port_separation / 2.0
    coupling_separation = gap + (wide_tip_width + narrow_tip_width) / 2.0
    coupling_top_y = coupling_center_offset + coupling_separation / 2.0
    coupling_bottom_y = coupling_center_offset - coupling_separation / 2.0
    output_top_y = output_center_offset + output_port_separation / 2.0
    output_bottom_y = output_center_offset - output_port_separation / 2.0

    top_left_lead = _straight_path(0.0, left_lead_length, input_top_y)
    bottom_left_lead = _straight_path(0.0, left_lead_length, input_bottom_y)
    top_left_transition_a, top_left_transition_b = _cosine_path_halves(
        left_lead_length,
        interaction_x0,
        input_top_y,
        coupling_top_y,
    )
    bottom_left_transition_a, bottom_left_transition_b = _cosine_path_halves(
        left_lead_length,
        interaction_x0,
        input_bottom_y,
        coupling_bottom_y,
    )

    taper_x1 = interaction_x0 + taper_length
    top_transfer_taper = _straight_path(interaction_x0, taper_x1, coupling_top_y)
    bottom_transfer_taper = _straight_path(interaction_x0, taper_x1, coupling_bottom_y)

    top_right_transition_a, top_right_transition_b = _cosine_path_halves(
        interaction_x1,
        output_transition_x1,
        coupling_top_y,
        output_top_y,
    )
    bottom_right_transition_a, bottom_right_transition_b = _cosine_path_halves(
        interaction_x1,
        output_transition_x1,
        coupling_bottom_y,
        output_bottom_y,
    )
    top_right_lead = _straight_path(
        output_transition_x1,
        output_x1,
        output_top_y,
    )
    bottom_right_lead = _straight_path(
        output_transition_x1,
        output_x1,
        output_bottom_y,
    )

    component.add_ref(_extrude_constant(top_left_lead, guide_width))
    component.add_ref(_extrude_constant(bottom_left_lead, guide_width))
    component.add_ref(
        _extrude_linear(top_left_transition_a, guide_width, left_top_bend_width)
    )
    component.add_ref(
        _extrude_linear(top_left_transition_b, left_top_bend_width, wide_tip_width)
    )
    component.add_ref(
        _extrude_linear(
            bottom_left_transition_a,
            guide_width,
            left_bottom_bend_width,
        )
    )
    component.add_ref(
        _extrude_linear(
            bottom_left_transition_b,
            left_bottom_bend_width,
            narrow_tip_width,
        )
    )
    component.add_ref(
        _extrude_linear(top_transfer_taper, wide_tip_width, guide_width)
    )
    component.add_ref(
        _extrude_linear(bottom_transfer_taper, narrow_tip_width, guide_width)
    )

    hold_length = transfer_length - taper_length
    if hold_length > 1e-9:
        top_transfer_hold = _straight_path(taper_x1, interaction_x1, coupling_top_y)
        bottom_transfer_hold = _straight_path(
            taper_x1,
            interaction_x1,
            coupling_bottom_y,
        )
        component.add_ref(_extrude_constant(top_transfer_hold, guide_width))
        component.add_ref(_extrude_constant(bottom_transfer_hold, guide_width))

    component.add_ref(
        _extrude_linear(top_right_transition_a, guide_width, right_top_bend_width)
    )
    component.add_ref(
        _extrude_linear(top_right_transition_b, right_top_bend_width, guide_width)
    )
    component.add_ref(
        _extrude_linear(
            bottom_right_transition_a,
            guide_width,
            right_bottom_bend_width,
        )
    )
    component.add_ref(
        _extrude_linear(
            bottom_right_transition_b,
            right_bottom_bend_width,
            guide_width,
        )
    )
    component.add_ref(_extrude_constant(top_right_lead, guide_width))
    component.add_ref(_extrude_constant(bottom_right_lead, guide_width))

    fixed_top_length = (
        top_left_lead.length()
        + top_left_transition_a.length()
        + top_left_transition_b.length()
        + top_right_transition_a.length()
        + top_right_transition_b.length()
        + top_right_lead.length()
    )
    fixed_bottom_length = (
        bottom_left_lead.length()
        + bottom_left_transition_a.length()
        + bottom_left_transition_b.length()
        + bottom_right_transition_a.length()
        + bottom_right_transition_b.length()
        + bottom_right_lead.length()
    )
    measured_transfer_length = top_transfer_taper.length() + max(hold_length, 0.0)

    lengths = {
        "arms": {
            "fixed_sections": fixed_top_length,
            "fixed_plus_transfer": fixed_top_length + measured_transfer_length,
        },
        "delta_length_um": measured_transfer_length,
        "coupler": {
            "length_um": measured_transfer_length,
            "gap_um": gap,
            "width_um": guide_width,
        },
        "paths": {
            "upper_total_um": fixed_top_length + measured_transfer_length,
            "lower_total_um": fixed_bottom_length + measured_transfer_length,
        },
    }
    Path(__file__).with_name("lengths.json").write_text(
        json.dumps(lengths, indent=2) + "\n"
    )
    return component


if __name__ == "__main__":
    device = adiabatic_directional_coupler()
    device.write_gds(
        Path(__file__).with_name("device.gds"),
        with_metadata=False,
    )
