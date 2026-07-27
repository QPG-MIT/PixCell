from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Functional top-level tunables, in um.
input_width_um = 0.52
input_taper_end_width_um = 1.00
input_taper_length_um = 10.00
mmi_width_um = 2.50
mmi_length_um = 5.50
output_taper_length_um = 10.00
output_start_width_um = 0.98
output_end_width_um = 0.52
output_center_separation_um = 1.27

SCRIPT_DIR = Path(__file__).resolve().parent
output_gds = SCRIPT_DIR / "device.gds"


@gf.cell
def build_device() -> gf.Component:
    c = gf.Component()

    x_body0 = input_taper_length_um
    x_body1 = x_body0 + mmi_length_um

    input_taper = gf.components.taper(
        length=input_taper_length_um,
        width1=input_width_um,
        width2=input_taper_end_width_um,
        layer=LAYER,
        with_bbox=False,
    )
    c << input_taper

    slab = gf.components.rectangle(
        size=(mmi_length_um, mmi_width_um),
        layer=LAYER,
        centered=False,
        port_type=None,
    )
    slab_ref = c << slab
    slab_ref.move((x_body0, -mmi_width_um / 2))

    branch_y = output_center_separation_um / 2
    output_taper = gf.components.taper(
        length=output_taper_length_um,
        width1=output_start_width_um,
        width2=output_end_width_um,
        layer=LAYER,
        with_bbox=False,
    )
    top_ref = c << output_taper
    top_ref.move((x_body1, branch_y))

    bottom_ref = c << output_taper
    bottom_ref.move((x_body1, -branch_y))

    c.flatten()
    return c


def write_lengths() -> None:
    # The splitter has two equal output routes. For the knob-response helper,
    # mmi_length_um is recorded as the functional interaction length.
    common_route_um = input_taper_length_um + output_taper_length_um
    payload = {
        "arms": {
            "upper": common_route_um + mmi_length_um,
            "lower": common_route_um,
        },
        "delta_length_um": mmi_length_um,
    }
    (SCRIPT_DIR / "lengths.json").write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    component = build_device()
    component.write_gds(output_gds, with_metadata=False)
    write_lengths()
