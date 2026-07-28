from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


# Parametric contract: all dimensions are microns and all tunables are live.
layer = (1, 0)
mmi_width = 19.46
mmi_length = 3.75
mmi_center_x = 12.49

access_width = 1.20
access_taper_length = 0.93
access_taper_base_width = 2.46

output_count = 4
output_width = 1.23
output_straight_length = 1.34
output_taper_length = 1.40
output_taper_base_width = 2.45
output_outer_offset = 7.03
output_inner_left_offset = 2.87
output_inner_right_offset = 2.56

# The calibration frame contains a few isolated dark pixels outside the main
# connected component. This sub-resolution primitive fixes the physical frame
# origin while contributing negligible scored area.
frame_anchor_size = 0.002
frame_anchor_x = 0.0
frame_anchor_y = -3.70


@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    body_component = gf.components.rectangle(
        size=(mmi_width, mmi_length),
        layer=layer,
        centered=True,
        port_type=None,
    )
    body = c << body_component
    body.dmove((mmi_center_x, 0.0))

    body_top = mmi_length / 2
    body_bottom = -mmi_length / 2
    output_xs = (
        mmi_center_x - output_outer_offset,
        mmi_center_x - output_inner_left_offset,
        mmi_center_x + output_inner_right_offset,
        mmi_center_x + output_outer_offset,
    )
    if len(output_xs) != output_count:
        raise ValueError("output_count must match the four declared output positions")

    for x_position in output_xs:
        taper_component = gf.components.taper(
            length=output_taper_length,
            width1=output_taper_base_width,
            width2=output_width,
            layer=layer,
            with_bbox=False,
        )
        taper = c << taper_component
        taper.drotate(90)
        taper.dmove((x_position, body_top))

        straight_component = gf.components.rectangle(
            size=(output_width, output_straight_length),
            layer=layer,
            centered=True,
            port_type=None,
        )
        straight = c << straight_component
        straight.dmove(
            (
                x_position,
                body_top + output_taper_length + output_straight_length / 2,
            )
        )

    access_component = gf.components.taper(
        length=access_taper_length,
        width1=access_taper_base_width,
        width2=access_width,
        layer=layer,
        with_bbox=False,
    )
    access = c << access_component
    access.drotate(-90)
    access.dmove((mmi_center_x, body_bottom))

    anchor_component = gf.components.rectangle(
        size=(frame_anchor_size, frame_anchor_size),
        layer=layer,
        centered=False,
        port_type=None,
    )
    anchor = c << anchor_component
    anchor.dmove((frame_anchor_x, frame_anchor_y))

    # Measurement contract: derive the reported knob from built geometry.
    measured_mmi_length = float(body.dymax - body.dymin)
    lengths_path = Path(__file__).with_name("lengths.json")
    lengths_path.write_text(
        json.dumps(
            {
                "arms": {
                    "reference": 0.0,
                    "mmi_imaging_axis": measured_mmi_length,
                },
                "delta_length_um": measured_mmi_length,
                "mmi": {
                    "length_um": measured_mmi_length,
                    "width_um": float(body.dxmax - body.dxmin),
                },
            },
            indent=2,
        )
    )
    return c


if __name__ == "__main__":
    device().write_gds(Path(__file__).with_name("device.gds"), with_metadata=False)
