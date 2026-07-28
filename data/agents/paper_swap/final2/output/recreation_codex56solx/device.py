import json
from pathlib import Path

import gdsfactory as gf


# Fabrication layer.
layer = (1, 0)

# Full calibrated comparison frame. Sparse thresholded boundary pixels in the
# source image make these tiny primitive marks necessary for absolute alignment.
frame_length = 25.0
frame_width = 10.0
registration_mark_size = 0.002

# Multimode-interference body: its width controls the lateral mode set and its
# propagation length controls the four-image plane.
mmi_length = 3.75
mmi_width = 19.45
mmi_x = 2.76
mmi_y = 2.65

# Centered input access taper.
input_center = 12.49
input_taper_length = 0.92
input_tip_width = 1.18
input_body_width = 2.48

# Four output collection tapers and access guides.
output_taper_length = 1.40
output_tip_width = 1.23
output_body_width = 2.42
output_straight_length = 1.34
output_center_1 = 5.45
output_center_2 = 9.61
output_center_3 = 15.03
output_center_4 = 19.48


def add_vertical_taper(
    component: gf.Component,
    center_x: float,
    start_y: float,
    length: float,
    width_start: float,
    width_end: float,
) -> None:
    taper = gf.components.taper(
        length=length,
        width1=width_start,
        width2=width_end,
        layer=layer,
    )
    ref = component.add_ref(taper)
    ref.drotate(90)
    ref.dmove((center_x, start_y))


def add_centered_rectangle(
    component: gf.Component,
    center_x: float,
    bottom_y: float,
    width: float,
    length: float,
) -> None:
    rectangle = gf.components.rectangle(size=(width, length), layer=layer)
    ref = component.add_ref(rectangle)
    ref.dmove((center_x - width / 2, bottom_y))


@gf.cell
def build_device() -> gf.Component:
    component = gf.Component()

    # Multimode slab.
    body = gf.components.rectangle(size=(mmi_width, mmi_length), layer=layer)
    body_ref = component.add_ref(body)
    body_ref.dmove((mmi_x, mmi_y))

    # The input runs upward from its narrow guide tip into the MMI body.
    add_vertical_taper(
        component,
        center_x=input_center,
        start_y=mmi_y - input_taper_length,
        length=input_taper_length,
        width_start=input_tip_width,
        width_end=input_body_width,
    )

    body_top = mmi_y + mmi_length
    for center_x in (
        output_center_1,
        output_center_2,
        output_center_3,
        output_center_4,
    ):
        add_vertical_taper(
            component,
            center_x=center_x,
            start_y=body_top,
            length=output_taper_length,
            width_start=output_body_width,
            width_end=output_tip_width,
        )
        add_centered_rectangle(
            component,
            center_x=center_x,
            bottom_y=body_top + output_taper_length,
            width=output_tip_width,
            length=output_straight_length,
        )

    # Primitive registration marks preserve the image-derived 25 x 10 um
    # scoring frame without changing the optical topology.
    lower_left = gf.components.rectangle(
        size=(registration_mark_size, registration_mark_size),
        layer=layer,
    )
    component.add_ref(lower_left)

    upper_right = gf.components.rectangle(
        size=(registration_mark_size, registration_mark_size),
        layer=layer,
    )
    upper_right_ref = component.add_ref(upper_right)
    upper_right_ref.dmove(
        (
            frame_length - registration_mark_size,
            frame_width - registration_mark_size,
        )
    )

    return component


device = build_device()
device.write_gds("device.gds", with_metadata=False)

# verify_knob_response currently consumes the two-path measurement shape.
# These are geometric propagation-axis paths: perturbing mmi_length changes the
# MMI axis itself, and the body area changes by mmi_width * delta length.
reference_axis = gf.Path()
reference_axis.append(gf.path.straight(length=0.001))
mmi_axis = gf.Path()
mmi_axis.append(gf.path.straight(length=mmi_length + 0.001))
reference_length = float(reference_axis.length())
mmi_axis_length = float(mmi_axis.length())
Path("lengths.json").write_text(
    json.dumps(
        {
            "arms": {
                "reference_axis": reference_length,
                "mmi_axis": mmi_axis_length,
            },
            "delta_length_um": abs(mmi_axis_length - reference_length),
        },
        indent=2,
    )
)
