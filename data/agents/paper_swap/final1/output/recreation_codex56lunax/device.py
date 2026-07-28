"""Primitive-only recreation of the three-rail tapered mode splitter."""

from pathlib import Path
import json

import gdsfactory as gf


LAYER = (1, 0)

# Function-defining tunables. ``delta_length`` is the central-rail tip-run
# contribution to the active transfer length; it is a constant-width run so
# the knob has a direct, measurable area response.
delta_length = 0.0
central_taper_length_um = 25.05
central_early_taper_length_um = 20.0
central_mid_width_um = 0.124
central_start_width_um = 0.270
central_tip_width_um = 0.070
outer_start_width_um = 0.066
outer_end_width_um = 0.240
rail_gap_um = 0.100
input_lead_um = 3.05
output_offset_um = 0.730
vertical_bias_um = 0.013
bend_length_um = 11.0
output_straight_length_um = 3.95
outer_taper_length_um = 22.0


def _outer_bend_path(sign: float = 1.0) -> gf.Path:
    rail_center_offset_um = (
        central_start_width_um / 2.0 + rail_gap_um + outer_start_width_um / 2.0
    )
    start_y = vertical_bias_um + sign * rail_center_offset_um
    end_y = sign * output_offset_um
    displacement = end_y - start_y
    points = []
    for index in range(101):
        t = index / 100.0
        smootherstep = 6.0 * t**5 - 15.0 * t**4 + 10.0 * t**3
        points.append((bend_length_um * t, displacement * smootherstep))
    return gf.Path(points)


def _write_lengths(component_path: Path) -> None:
    # The active centerline lengths are derived from the primitive taper/run
    # dimensions rather than worker claims.
    central_length_um = central_taper_length_um + delta_length
    outer_length_um = outer_taper_length_um
    payload = {
        "arms": {
            "central": central_length_um,
            "outer_reference": outer_length_um,
        },
        "delta_length_um": abs(outer_length_um - central_length_um),
        "path": {"total_um": central_length_um},
    }
    component_path.with_name("lengths.json").write_text(json.dumps(payload, indent=2))


@gf.cell
def three_rail_splitter() -> gf.Component:
    component = gf.Component("three_rail_splitter")

    # The central rail is a linear taper followed by a short tip run.  Keeping
    # the tail separate makes delta_length a real geometry knob.
    central_early_taper = gf.components.taper(
        length=central_early_taper_length_um,
        width1=central_start_width_um,
        width2=central_mid_width_um,
        layer=LAYER,
        with_bbox=False,
    )
    central_ref = component.add_ref(central_early_taper)
    central_ref.movey(vertical_bias_um)

    central_late_taper = gf.components.taper(
        length=central_taper_length_um - central_early_taper_length_um,
        width1=central_mid_width_um,
        width2=central_tip_width_um,
        layer=LAYER,
        with_bbox=False,
    )
    central_late_ref = component.add_ref(central_late_taper)
    central_late_ref.move((central_early_taper_length_um, vertical_bias_um))
    central_tail_um = max(0.0, delta_length)
    if central_tail_um > 0:
        central_tail = gf.path.straight(length=central_tail_um).extrude(
            width=central_tip_width_um, layer=LAYER
        )
        central_tail_ref = component.add_ref(central_tail)
        central_tail_ref.move((central_taper_length_um, vertical_bias_um))

    rail_center_offset_um = (
        central_start_width_um / 2.0 + rail_gap_um + outer_start_width_um / 2.0
    )

    # Both outer rails expand over the same active region as the image, then
    # continue with constant-width smooth paths to the separated outputs.
    outer_taper = gf.components.taper(
        length=outer_taper_length_um,
        width1=outer_start_width_um,
        width2=outer_end_width_um,
        layer=LAYER,
        with_bbox=False,
    )
    top_taper_ref = component.add_ref(outer_taper)
    top_taper_ref.move((input_lead_um, vertical_bias_um + rail_center_offset_um))
    bottom_taper_ref = component.add_ref(outer_taper)
    bottom_taper_ref.move((input_lead_um, vertical_bias_um - rail_center_offset_um))

    top_bend_path = _outer_bend_path()
    top_bend = top_bend_path.extrude(width=outer_end_width_um, layer=LAYER)
    top_bend_ref = component.add_ref(top_bend)
    top_bend_ref.move((input_lead_um + outer_taper_length_um, vertical_bias_um + rail_center_offset_um))

    bottom_bend_path = _outer_bend_path(sign=-1.0)
    bottom_bend = bottom_bend_path.extrude(width=outer_end_width_um, layer=LAYER)
    bottom_bend_ref = component.add_ref(bottom_bend)
    bottom_bend_ref.move((input_lead_um + outer_taper_length_um, vertical_bias_um - rail_center_offset_um))

    output_x_um = input_lead_um + outer_taper_length_um + bend_length_um
    output_straight = gf.path.straight(length=output_straight_length_um).extrude(
        width=outer_end_width_um, layer=LAYER
    )
    top_output_ref = component.add_ref(output_straight)
    top_output_ref.move((output_x_um, output_offset_um))
    bottom_output_ref = component.add_ref(output_straight)
    bottom_output_ref.move((output_x_um, -output_offset_um))

    return component


device = three_rail_splitter()
here = Path(__file__).resolve().parent
_write_lengths(here / "device.gds")
device.write_gds(here / "device.gds", with_metadata=False)
