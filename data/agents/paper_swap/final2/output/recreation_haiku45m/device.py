"""1x4 Multimode Interferometer (MMI) — primitives-only recreation."""

import gdsfactory as gf
import json
from pathlib import Path

# Tunable parameters
wg_width = 0.5  # μm, output waveguide width
mmi_width = 24.0  # μm, multimode core width
mmi_height = 7.0  # μm, MMI core height
taper_length = 1.0  # μm, short taper from MMI to wg
taper_width_mmi = 2.2  # μm, taper width at MMI end (compact ports)
port_spacing = 5.8  # μm, spacing between 4 output port centers
layer = (1, 0)

@gf.cell
def mmi_1x4():
    """1x4 MMI with tapered I/O — footprint-matching recreation."""
    c = gf.Component()

    # Central MMI core: wide rectangle
    mmi_rect = gf.components.rectangle(size=(mmi_width, mmi_height), layer=layer)
    ref_mmi = c.add_ref(mmi_rect)
    ref_mmi.movey(-mmi_height / 2)

    # Input taper at the bottom: wide→narrow (MMI to waveguide)
    input_taper = gf.components.taper(
        length=taper_length,
        width1=taper_width_mmi,
        width2=wg_width,
        layer=layer
    )
    ref_input = c.add_ref(input_taper)
    ref_input.rotate(180)
    ref_input.movey(-mmi_height / 2 - taper_length)

    # Four output tapers at the top: narrow→wide (waveguide from MMI)
    # Positioned at ±3, ±1 port_spacing/2 across the MMI width
    port_x_positions = [
        -3 * port_spacing / 2,
        -1 * port_spacing / 2,
        1 * port_spacing / 2,
        3 * port_spacing / 2,
    ]

    for x_offset in port_x_positions:
        output_taper = gf.components.taper(
            length=taper_length,
            width1=wg_width,
            width2=taper_width_mmi,
            layer=layer
        )
        ref_out = c.add_ref(output_taper)
        ref_out.movex(x_offset)
        ref_out.movey(mmi_height / 2)

    return c

if __name__ == "__main__":
    cell = mmi_1x4()

    # Write GDS
    gds_path = "device.gds"
    cell.write_gds(gds_path)
    print(f"GDS written to {gds_path}")

    # Write a dummy lengths.json for spec_optimization compatibility
    lengths_data = {
        "arms": {
            "mmi_core": {
                "length_um": mmi_height
            }
        },
        "delta_length_um": 0.0
    }
    with open("lengths.json", "w") as f:
        json.dump(lengths_data, f, indent=2)
    print(f"lengths.json written")
