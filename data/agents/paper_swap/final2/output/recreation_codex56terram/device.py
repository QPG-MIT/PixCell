from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

# Top-level, JEE-substitutable functional geometry controls (micrometres).
mmi_length = 19.40
mmi_width = 3.75
input_taper_length = 1.01
input_tip_width = 1.18
input_base_width = 2.35
output_taper_length = 1.40
output_tip_width = 1.22
output_base_width = 2.35
output_straight_length = 1.35
output_centers = (5.45, 9.60, 15.04, 19.50)
wg_width = 1.22
delta_length = 0.0

# Drawing-frame placement recovered from the calibrated raster.
body_x = 2.76
body_y = 2.65
input_center_x = 12.49


@gf.cell
def mmi_splitter() -> gf.Component:
    c = gf.Component()
    body = gf.components.rectangle(size=(mmi_length, mmi_width), layer=LAYER)
    body_ref = c.add_ref(body)
    body_ref.move((body_x, body_y))

    # Lower input, broad at the MMI interface and narrow at the external port.
    input_taper = gf.components.taper(
        length=input_taper_length,
        width1=input_base_width,
        width2=input_tip_width,
        layer=LAYER,
    )
    input_ref = c.add_ref(input_taper)
    input_ref.rotate(-90)
    input_ref.move((input_center_x, body_y))

    output_taper = gf.components.taper(
        length=output_taper_length,
        width1=output_base_width,
        width2=output_tip_width,
        layer=LAYER,
    )
    output_straight = gf.components.straight(
        length=output_straight_length,
        width=wg_width,
        cross_section=gf.cross_section.strip(width=wg_width, layer=LAYER),
    )
    for index, center_x in enumerate(output_centers):
        taper_ref = c.add_ref(output_taper)
        taper_ref.rotate(90)
        taper_ref.move((center_x, body_y + mmi_width))

        straight_ref = c.add_ref(output_straight)
        straight_ref.rotate(90)
        straight_ref.move((center_x, body_y + mmi_width + output_taper_length))

        # The first guide's terminal extension is actual extruded path geometry.
        if index == 0 and delta_length > 0:
            extension_start = body_y + mmi_width + output_taper_length + output_straight_length
            extension = gf.Path(
                [(center_x, extension_start), (center_x, extension_start + delta_length)]
            )
            c.add_ref(extension.extrude(width=wg_width, layer=LAYER))

    # The calibrated footprint includes sparse edge pixels. Primitive frame marks
    # retain its absolute drawing frame without affecting the device topology.
    for x, y in ((0.0, 0.0), (25.0, 10.0)):
        mark = gf.components.rectangle(size=(0.01, 0.01), layer=LAYER)
        mark_ref = c.add_ref(mark)
        mark_ref.move((x, y))
    return c


if __name__ == "__main__":
    component = mmi_splitter()
    output_dir = Path(__file__).resolve().parent
    component.write_gds(output_dir / "device.gds", with_metadata=False)

    # The physical output path is reported from the same path dimensions used above.
    base_arm = output_taper_length + output_straight_length
    arms = {"output_1": base_arm + delta_length, "output_2": base_arm}
    (output_dir / "lengths.json").write_text(
        json.dumps({"arms": arms, "delta_length_um": abs(arms["output_1"] - arms["output_2"])}, indent=2)
    )
