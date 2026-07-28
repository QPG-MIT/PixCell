"""Primitives-only 1x4 MMI recreation for the calibrated paper-swap target."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Supplied calibrated scoring frame (um).
footprint_length = 25.0
footprint_width = 10.0
frame_tab_um = 0.002

# Multimode slab: all image-defining dimensions are live, top-level tunables.
slab_left = 2.7762040
slab_bottom = 2.6563877
slab_width = 19.4334278
slab_length = 3.7488987

# Four-way port array and upper transitions.
guide_width = 1.2300000
top_taper_length = 1.4140969
top_taper_width = 2.4700000
top_straight_length = 1.3215859
output_center_1 = 5.4532578
output_center_2 = 9.6246459
output_center_3 = 15.0495751
output_center_4 = 19.5042493

# Center input transition. input_extension is a genuine guide-length knob;
# its zero baseline preserves the supplied silhouette while a perturbation
# grows one physical guide by guide_width * input_extension.
input_center_x = 12.4929178
input_taper_length = 0.9251101
input_taper_width = 2.4640000
input_extension = 0.0


@gf.cell
def vertical_straight(center_x: float, y0: float, y1: float, width: float) -> gf.Component:
    """A primitive vertical guide made by extruding its explicit centerline."""
    centerline = gf.Path([(center_x, y0), (center_x, y1)])
    return centerline.extrude(width=width, layer=LAYER)


@gf.cell
def mmi_1x4() -> gf.Component:
    """Assemble the slab, four upper ports, one lower port, and frame tabs."""
    c = gf.Component()

    slab = c.add_ref(
        gf.components.rectangle(size=(slab_width, slab_length), layer=LAYER, centered=False)
    )
    slab.dmove((slab_left, slab_bottom))

    slab_top = slab_bottom + slab_length
    for center_x in (
        output_center_1,
        output_center_2,
        output_center_3,
        output_center_4,
    ):
        flare = c.add_ref(
            gf.components.taper(
                length=top_taper_length,
                width1=top_taper_width,
                width2=guide_width,
                layer=LAYER,
                with_bbox=False,
            )
        )
        flare.drotate(90)
        flare.dmove((center_x, slab_top))
        c.add_ref(
            vertical_straight(
                center_x,
                slab_top + top_taper_length,
                slab_top + top_taper_length + top_straight_length,
                guide_width,
            )
        )

    input_flare = c.add_ref(
        gf.components.taper(
            length=input_taper_length,
            width1=input_taper_width,
            width2=guide_width,
            layer=LAYER,
            with_bbox=False,
        )
    )
    input_flare.drotate(-90)
    input_flare.dmove((input_center_x, slab_bottom))

    if input_extension > 0.0:
        c.add_ref(
            vertical_straight(
                input_center_x,
                slab_bottom - input_taper_length,
                slab_bottom - input_taper_length - input_extension,
                guide_width,
            )
        )

    # Primitive registration tabs retain the measured empty margins in the
    # absolute-calibration frame without changing visible device topology.
    lower_tab = c.add_ref(
        gf.components.rectangle(size=(frame_tab_um, frame_tab_um), layer=LAYER, centered=False)
    )
    lower_tab.dmove((0.0, 0.0))
    upper_tab = c.add_ref(
        gf.components.rectangle(size=(frame_tab_um, frame_tab_um), layer=LAYER, centered=False)
    )
    upper_tab.dmove((footprint_length - frame_tab_um, footprint_width - frame_tab_um))

    return c


def write_lengths() -> None:
    """Write centerline-derived lengths for the real input-extension knob."""
    reference_arm = gf.Path(
        [
            (input_center_x, slab_bottom),
            (input_center_x, slab_bottom - input_taper_length),
        ]
    )
    extended_arm = gf.Path(
        [
            (input_center_x, slab_bottom),
            (input_center_x, slab_bottom - input_taper_length - input_extension),
        ]
    )
    reference_length = float(reference_arm.length())
    extended_length = float(extended_arm.length())
    payload = {
        "arms": {"reference": reference_length, "extended": extended_length},
        "delta_length_um": abs(extended_length - reference_length),
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    component = mmi_1x4().dup()
    component.flatten()
    write_lengths()
    component.write_gds(Path(__file__).with_name("device.gds"))
