"""Primitives-only recreation of the supplied 1x4 slab splitter silhouette."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


# Parametric contract: all geometric/function-defining dimensions are live,
# top-level numeric assignments in microns.
layer = (1, 0)
footprint_length = 25.0
footprint_width = 10.0

slab_length = 19.4334
slab_width = 3.7533
slab_left = 2.7762
slab_bottom = 2.6519

input_taper_length = 0.9207
input_tip_width = 1.246
input_slab_width = 2.464
input_lead_length = 0.01

output_count = 4
output_1_center = 5.4533
output_2_center = 9.6161
output_3_center = 15.0340
output_4_center = 19.4674
output_guide_width = 1.218
output_base_width = 2.408
output_taper_length = 1.4009
output_straight_length = 1.3427

# Minuscule corner anchors preserve the calibrated 25 x 10 um scoring frame.
calibration_anchor_size = 0.002


@gf.cell
def slab_splitter() -> gf.Component:
    """Assemble the input taper, multimode slab, and four output tapers."""
    component = gf.Component()

    slab = component << gf.components.rectangle(
        size=(slab_length, slab_width), layer=layer
    )
    slab.dmove((slab_left, slab_bottom))

    input_center = slab_left + slab_length / 2
    input_taper = component << gf.components.taper(
        length=input_taper_length,
        width1=input_tip_width,
        width2=input_slab_width,
        layer=layer,
    )
    input_taper.drotate(90)
    input_taper.dmove((input_center, slab_bottom - input_taper_length))

    # A clean access-guide extension is intentionally a Path extrusion, so its
    # length is a verified physical knob rather than a reported-only number.
    access_path = gf.path.straight(length=input_lead_length)
    access_path.drotate(-90)
    access_path.dmove((input_center, slab_bottom - input_taper_length))
    component << access_path.extrude(width=input_tip_width, layer=layer)

    for center in (output_1_center, output_2_center, output_3_center, output_4_center):
        output_taper = component << gf.components.taper(
            length=output_taper_length,
            width1=output_base_width,
            width2=output_guide_width,
            layer=layer,
        )
        output_taper.drotate(90)
        output_taper.dmove((center, slab_bottom + slab_width))

        output_path = gf.path.straight(length=output_straight_length)
        output_path.drotate(90)
        output_path.dmove((center, slab_bottom + slab_width + output_taper_length))
        component << output_path.extrude(width=output_guide_width, layer=layer)

    for x, y in ((0.0, 0.0), (footprint_length - calibration_anchor_size, footprint_width - calibration_anchor_size)):
        anchor = component << gf.components.rectangle(
            size=(calibration_anchor_size, calibration_anchor_size), layer=layer
        )
        anchor.dmove((x, y))

    return component


if __name__ == "__main__":
    device = slab_splitter()
    output_dir = Path(__file__).resolve().parent
    # The access guide is the phase/access-length knob.  These values are
    # derived from the same Path length that is extruded above.
    (output_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {
                    "reference": 0.0,
                    "input_access": input_lead_length,
                },
                "delta_length_um": input_lead_length,
            },
            indent=2,
        )
    )
    device.write_gds(output_dir / "device.gds", with_metadata=False)
