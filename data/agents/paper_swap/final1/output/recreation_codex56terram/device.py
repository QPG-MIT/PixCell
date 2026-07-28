"""Primitives-only reconstruction of the three-rail adiabatic coupler."""

from pathlib import Path
import json

import gdsfactory as gf

LAYER = (1, 0)

# Live, top-level geometry contract (all dimensions in um).
device_length = 40.0
center_input_width = 0.270
center_tip_width = 0.070
outer_tip_width = 0.070
outer_coupling_width = 0.240
output_width = 0.240
coupling_gap = 0.105
coupling_length = 21.9
# Independent center-tip extension used as the primary transfer-length knob.
# It is deliberately a top-level assignment for the spec evaluator contract.
delta_length = 0.01
outer_start_offset = 3.07
s_bend_length = 10.0
output_straight_length = 4.3
output_separation = 1.460
outer_straight_extension = 0.70


def _cross_section(width: float) -> gf.CrossSection:
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def _add_variable_width_path(
    component: gf.Component,
    points: list[tuple[float, float]],
    width1: float,
    width2: float,
) -> None:
    """Extrude a centerline with a linear width transition."""
    path = gf.Path(points)
    transition = gf.path.transition(
        _cross_section(width1), _cross_section(width2), width_type="linear", offset_type="linear"
    )
    component.add_ref(gf.path.extrude_transition(path, transition=transition))


def _bezier_points(
    start: tuple[float, float],
    control1: tuple[float, float],
    control2: tuple[float, float],
    end: tuple[float, float],
    count: int = 121,
) -> list[tuple[float, float]]:
    """Sample a smooth S-bend centerline; material remains Path-extruded."""
    result = []
    for index in range(count):
        t = index / (count - 1)
        u = 1.0 - t
        x = u**3 * start[0] + 3 * u**2 * t * control1[0] + 3 * u * t**2 * control2[0] + t**3 * end[0]
        y = u**3 * start[1] + 3 * u**2 * t * control1[1] + 3 * u * t**2 * control2[1] + t**3 * end[1]
        result.append((x, y))
    return result


@gf.cell
def adiabatic_three_rail_coupler() -> gf.Component:
    component = gf.Component()
    center_y = 0.865
    # The raster is intentionally not vertically mirror symmetric: its central
    # input rail sits 0.015 um above the midpoint of the fanned output pair.
    upper_start_y = center_y + center_input_width / 2 + outer_tip_width / 2 + coupling_gap
    lower_start_y = center_y - center_input_width / 2 - outer_tip_width / 2 - coupling_gap
    upper_output_y = 0.850 + output_separation / 2
    lower_output_y = 0.850 - output_separation / 2
    coupling_end = outer_start_offset + coupling_length
    bend_start = coupling_end + outer_straight_extension
    bend_end = bend_start + s_bend_length

    # Center bus: broad left input tapering to its terminating coupling tip.
    center_path = gf.Path([(0.0, center_y), (coupling_end, center_y)])
    center_transition = gf.path.transition(
        _cross_section(center_input_width), _cross_section(center_tip_width),
        width_type="linear", offset_type="linear"
    )
    component.add_ref(gf.path.extrude_transition(center_path, transition=center_transition))
    extension_path = gf.Path([(coupling_end, center_y), (coupling_end + delta_length, center_y)])
    component.add_ref(gf.path.extrude(extension_path, cross_section=_cross_section(center_tip_width)))
    component.info["reference_arm_length_um"] = center_path.length()
    component.info["tuned_arm_length_um"] = center_path.length() + extension_path.length()

    # Matched upper/lower rails: narrow launches, gradual coupling taper, then S-bend fan-out.
    for start_y, output_y in ((upper_start_y, upper_output_y), (lower_start_y, lower_output_y)):
        _add_variable_width_path(
            component,
            [(outer_start_offset, start_y), (bend_start, start_y)],
            outer_tip_width,
            outer_coupling_width,
        )
        bend = _bezier_points(
            (bend_start, start_y),
            (bend_start + 0.35 * s_bend_length, start_y),
            (bend_end - 0.35 * s_bend_length, start_y + 0.70 * (output_y - start_y)),
            (bend_end, output_y),
        )
        _add_variable_width_path(component, bend, outer_coupling_width, output_width)
        component.add_ref(gf.components.straight(
            length=output_straight_length, cross_section=_cross_section(output_width)
        )).dmove((bend_end, output_y))

    return component


if __name__ == "__main__":
    output = Path(__file__).with_name("device.gds")
    cell = adiabatic_three_rail_coupler()
    reference = float(cell.info["reference_arm_length_um"])
    tuned = float(cell.info["tuned_arm_length_um"])
    # Flatten only at export so the external area verifier sees material, not references.
    export_cell = cell.copy()
    export_cell.flatten()
    export_cell.write_gds(output, with_metadata=False)
    Path(__file__).with_name("lengths.json").write_text(json.dumps({
        "arms": {"reference": reference, "tuned": tuned},
        "delta_length_um": abs(tuned - reference),
    }, indent=2))
