import gdsfactory as gf

@gf.cell
def device_1x4_mmi():
    """
    1x4 MMI Splitter.
    Reconstructed to fit the [25, 10] um footprint with refined proportions
    matching the target image.
    
    Dimensions:
    - MMI Body: 10 x 8 um
    - Output Tapers: 12 um long, tapering from 2.3um to 0.8um
    - Input Taper: 5 um long, tapering from 3.2um to 1.0um
    """
    c = gf.Component()
    layer = (1, 0)

    # --- Dimensions & Parameters ---
    
    # 1. Main MMI Body
    # A solid rectangular block
    mmi_width = 10.0
    mmi_height = 8.0 

    # 2. Output Tapers (Top)
    # Long linear tapers that start wide (creating narrow gaps) and narrow down.
    # Total Height Budget: 25um. Body=8, Input=5 -> Output=12.
    taper_length_out = 12.0
    n_outputs = 4
    port_pitch = mmi_width / n_outputs  # 2.5 um
    
    # Widths: 
    # Base: 2.3um leaves a 0.2um gap between waveguides (Visual match for slit).
    # Tip: 0.8um for standard waveguide width at output.
    taper_width_out_base = 2.3
    taper_width_out_tip = 0.8

    # 3. Input Taper (Bottom)
    taper_length_in = 5.0
    taper_width_in_base = 3.2   # Wider base connecting to body
    taper_width_in_tip = 1.0

    # --- Geometry Construction ---

    # 1. Create Main Body
    # Centered at (0,0)
    body = c << gf.components.rectangle(
        size=(mmi_width, mmi_height), 
        layer=layer, 
        centered=True
    )

    # 2. Create and Place Output Tapers (Top)
    taper_out_comp = gf.components.taper(
        length=taper_length_out,
        width1=taper_width_out_base,
        width2=taper_width_out_tip,
        layer=layer
    )

    # Calculate offsets for 4 ports centered around 0
    # Formula: (i - (N-1)/2) * pitch
    offsets = [(i - (n_outputs - 1) / 2) * port_pitch for i in range(n_outputs)]

    for x_offset in offsets:
        ref = c << taper_out_comp
        ref.rotate(90)  # Rotate to point Up
        # Move base (width1) to the top edge of the body
        ref.move((x_offset, mmi_height / 2))

    # 3. Create and Place Input Taper (Bottom)
    taper_in_comp = gf.components.taper(
        length=taper_length_in,
        width1=taper_width_in_base,
        width2=taper_width_in_tip,
        layer=layer
    )

    ref_in = c << taper_in_comp
    ref_in.rotate(-90) # Rotate to point Down
    # Move base (width1) to the bottom edge of the body
    ref_in.move((0, -mmi_height / 2))

    return c

if __name__ == "__main__":
    device = device_1x4_mmi()
    device.write_gds("device_1x4_mmi.gds")