import gdsfactory as gf

# Top-level tunables (function-defining knobs for MMI 1x4 splitter)
# BEST from iteration 3: IoU=0.519
input_wg_width = 1.2  # Input waveguide width
input_taper_width = 3.5  # Width where input meets MMI body
input_taper_length = 0.9  # Input taper length
mmi_width = 22.0  # MMI body width (critical for mode interference)
mmi_length = 4.2  # MMI body length (critical for 1x4 splitting)
output_taper_tip_width = 0.8  # Narrow neck of output tapers
output_taper_length = 2.2  # Output taper length (critical for adiabatic transition)
output_wg_width = 1.0  # Final output waveguide width
output_spacing = 5.5  # Center-to-center spacing between outputs
output_extension = 1.8  # Straight section after tapers
input_section_length = 0.8  # Straight input before taper

# Platform constants
layer = (1, 0)


@gf.cell
def splitter_1x4(
    input_wg_width: float = 1.2,
    input_taper_width: float = 3.5,
    input_taper_length: float = 0.9,
    mmi_width: float = 22.0,
    mmi_length: float = 4.2,
    output_taper_tip_width: float = 0.8,
    output_taper_length: float = 2.2,
    output_wg_width: float = 1.0,
    output_spacing: float = 5.5,
    output_extension: float = 1.8,
    input_section_length: float = 0.8,
) -> gf.Component:
    """1x4 MMI splitter using primitives only."""
    c = gf.Component()

    y = 0

    # Input straight waveguide
    pts_input = [
        (-input_wg_width / 2, y),
        (input_wg_width / 2, y),
        (input_wg_width / 2, y + input_section_length),
        (-input_wg_width / 2, y + input_section_length),
    ]
    c.add_polygon(pts_input, layer=layer)
    y += input_section_length

    # Input taper (waveguide -> input_taper_width before MMI)
    pts_in_taper = [
        (-input_wg_width / 2, y),
        (input_wg_width / 2, y),
        (input_taper_width / 2, y + input_taper_length),
        (-input_taper_width / 2, y + input_taper_length),
    ]
    c.add_polygon(pts_in_taper, layer=layer)
    y += input_taper_length

    # MMI body
    pts_mmi = [
        (-mmi_width / 2, y),
        (mmi_width / 2, y),
        (mmi_width / 2, y + mmi_length),
        (-mmi_width / 2, y + mmi_length),
    ]
    c.add_polygon(pts_mmi, layer=layer)
    y += mmi_length

    # Four output positions
    n_outputs = 4
    total_span = (n_outputs - 1) * output_spacing
    x_positions = [
        -total_span / 2 + i * output_spacing for i in range(n_outputs)
    ]

    for x_center in x_positions:
        # Output taper (starts at output_taper_tip_width, widens to output_wg_width)
        pts_taper = [
            (x_center - output_taper_tip_width / 2, y),
            (x_center + output_taper_tip_width / 2, y),
            (x_center + output_wg_width / 2, y + output_taper_length),
            (x_center - output_wg_width / 2, y + output_taper_length),
        ]
        c.add_polygon(pts_taper, layer=layer)

        # Output waveguide extension
        pts_out = [
            (x_center - output_wg_width / 2, y + output_taper_length),
            (x_center + output_wg_width / 2, y + output_taper_length),
            (x_center + output_wg_width / 2, y + output_taper_length + output_extension),
            (x_center - output_wg_width / 2, y + output_taper_length + output_extension),
        ]
        c.add_polygon(pts_out, layer=layer)

    return c


if __name__ == "__main__":
    c = splitter_1x4(
        input_wg_width=input_wg_width,
        input_taper_width=input_taper_width,
        input_taper_length=input_taper_length,
        mmi_width=mmi_width,
        mmi_length=mmi_length,
        output_taper_tip_width=output_taper_tip_width,
        output_taper_length=output_taper_length,
        output_wg_width=output_wg_width,
        output_spacing=output_spacing,
        output_extension=output_extension,
        input_section_length=input_section_length,
    )
    c.write_gds("device.gds")
    print(f"Generated device.gds")
