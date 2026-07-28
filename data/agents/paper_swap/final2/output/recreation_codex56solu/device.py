import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Calibrated comparison frame.
footprint_length = 25.0
footprint_width = 10.0
calibration_anchor_size = 0.01

# Multimode transfer region.
mmi_width = 19.433
transfer_length = 3.753
body_left = 2.776
body_bottom = 2.652

# Single-guide and taper dimensions.
guide_width = 1.22
output_taper_length = 1.405
output_taper_base_width_1 = 2.44
output_taper_base_width_2 = 2.47
output_taper_base_width_3 = 2.45
output_taper_base_width_4 = 2.53
output_center_1 = 5.453
output_center_2 = 9.624
output_center_3 = 15.043
output_center_4 = 19.497

# Output 1 is the phase-trimmed path used for the physical knob-response test.
phase_trim_length = 1.315
output_straight_length = 1.315

# Centered input transition.
input_center = 12.493
input_taper_length = 0.921
input_taper_base_width = 2.465
input_tip_width = 1.16


phase_trim_path = gf.Path()
phase_trim_path.append(gf.path.straight(length=phase_trim_length))

reference_output_path = gf.Path()
reference_output_path.append(gf.path.straight(length=output_straight_length))


def add_vertical_reference(
    parent: gf.Component,
    child: gf.Component,
    x: float,
    y: float,
) -> None:
    reference = parent.add_ref(child)
    reference.drotate(90)
    reference.dmove((x, y))


@gf.cell
def build_device() -> gf.Component:
    component = gf.Component()

    body = gf.components.rectangle(
        size=(mmi_width, transfer_length),
        layer=LAYER,
        port_type=None,
        port_orientations=(),
    )
    body_ref = component.add_ref(body)
    body_ref.dmove((body_left, body_bottom))

    body_top = body_bottom + transfer_length
    output_centers = (
        output_center_1,
        output_center_2,
        output_center_3,
        output_center_4,
    )
    output_base_widths = (
        output_taper_base_width_1,
        output_taper_base_width_2,
        output_taper_base_width_3,
        output_taper_base_width_4,
    )

    for center, base_width in zip(output_centers, output_base_widths):
        taper = gf.components.taper(
            length=output_taper_length,
            width1=base_width,
            width2=guide_width,
            layer=LAYER,
        )
        add_vertical_reference(component, taper, center, body_top)

    phase_guide = gf.path.extrude(
        phase_trim_path,
        layer=LAYER,
        width=guide_width,
    )
    reference_guide = gf.path.extrude(
        reference_output_path,
        layer=LAYER,
        width=guide_width,
    )
    guide_start_y = body_top + output_taper_length
    add_vertical_reference(
        component,
        phase_guide,
        output_center_1,
        guide_start_y,
    )
    for center in output_centers[1:]:
        add_vertical_reference(
            component,
            reference_guide,
            center,
            guide_start_y,
        )

    input_taper = gf.components.taper(
        length=input_taper_length,
        width1=input_tip_width,
        width2=input_taper_base_width,
        layer=LAYER,
    )
    add_vertical_reference(
        component,
        input_taper,
        input_center,
        body_bottom - input_taper_length,
    )

    # Near-zero-area frame anchors preserve the whitespace encoded by the
    # supplied absolute calibration without changing the optical topology.
    anchor = gf.components.rectangle(
        size=(calibration_anchor_size, calibration_anchor_size),
        layer=LAYER,
        port_type=None,
        port_orientations=(),
    )
    component.add_ref(anchor)
    upper_anchor = component.add_ref(anchor)
    upper_anchor.dmove(
        (
            footprint_length - calibration_anchor_size,
            footprint_width - calibration_anchor_size,
        )
    )

    return component


component = build_device()

phase_length_um = phase_trim_path.length()
reference_length_um = reference_output_path.length()
length_payload = {
    "arms": {
        "phase_trimmed_output": phase_length_um,
        "reference_output": reference_length_um,
    },
    "delta_length_um": abs(phase_length_um - reference_length_um),
}
Path(__file__).with_name("lengths.json").write_text(
    json.dumps(length_payload, indent=2)
)

component.write_gds("device.gds", with_metadata=False)
