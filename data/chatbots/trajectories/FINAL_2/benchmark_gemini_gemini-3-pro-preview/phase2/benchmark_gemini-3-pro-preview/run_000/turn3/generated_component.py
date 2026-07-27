import gdsfactory as gf

@gf.cell
def device_1x4_mmi():
    """
    1x4 MMI Splitter.
    Reconstructed to fit the [25, 10] um footprint with refined proportions.
    
    Dimensions:
    - Width: 10 um
    - Height: 25 um (Top Tapers: 12um, Body: 8um, Bottom Taper: 5um)
    """
    c = gf.Component()

    # --- Dimensions & Parameters ---
    layer = (1, 0)

    # 1. Main MMI Body
    # Visually the body is a block spanning the full width.
    mmi_width = 10.0
    mmi_height = 8.0 

    # 2. Output Tapers (Top)
    # Long, slender linear tapers.
    taper_length_out = 12.0
    # Wide base to minimize gaps at the junction, narrowing at the tip.
    taper_width_out_base = 2.2  # Pitch is 2.5, so gap is 0.3um
    taper_width_out_tip = 1.0

    # 3. Input Taper (Bottom)
    # Shorter, triangular shape.
    taper_length_in = 5.0
    taper_width_in_base = 3.0   # Slightly wider connection at the body
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

    # Calculate positioning for 4 ports distributed across 10um
    num_ports = 4
    port_pitch = mmi_width / num_ports # 2.5 um
    
    # Calculate offsets: [-3.75, -1.25, 1.25, 3.75]
    offsets = [(i - (num_ports - 1) / 2) * port_pitch for i in range(num_ports)]

    for x_offset in offsets:
        ref = c << taper_out_comp
        ref.rotate(90)  # Rotate to point Up
        # Move to top edge of body
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
    # Move to bottom edge of body
    ref_in.move((0, -mmi_height / 2))

    return c

if __name__ == "__main__":
    device = device_1x4_mmi()
    device.write_gds("device_1x4_mmi.gds")