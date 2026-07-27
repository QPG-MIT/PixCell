import gdsfactory as gf

@gf.cell
def device_mmi_1x4_optimized():
    """
    1x4 MMI Power Splitter - Visual Match Optimization
    
    Adjustments from previous iteration:
    - MMI Body: Changed dimensions from 10.0x8.0 (tall) to 10.0x4.8 (wide slab).
      This corrects the aspect ratio to match the horizontal rectangular block in the target image.
    - Output Arms: Increased taper base width to 1.8um. With a 2.0um pitch, this creates
      the characteristic narrow 'V' gaps between the output arms seen in the target.
    - Input Arm: Widened the base to 3.0um and shortened the length to 2.5um to match
      the stout, triangular input stub appearance.
    - General: Increased waveguide width to 0.6um to match the line weight of the target.
    """
    c = gf.Component()
    
    # Layer definition
    layer = (1, 0)
    
    # --- Dimensions ---
    # MMI Body - The "Slab"
    # Target image shows a horizontal rectangle (Width > Height)
    mmi_width = 10.0
    mmi_height = 4.8
    
    # Output Arms (Top) configuration
    num_ports = 4
    pitch = 2.0
    
    top_taper_len = 7.0      # Elongated taper to match slender look
    top_straight_len = 5.0   # Significant straight section
    taper_top_base = 1.8     # Wide base creates 0.2um gap between adjacent tapers
    
    # Input Arm (Bottom) configuration
    bot_taper_len = 2.5      # Short, wide stub
    taper_bot_base = 3.0     # Wide connection to MMI body
    
    # Waveguide width
    wg_width = 0.6
    
    # Cross Section for straights
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # --- Geometry Construction ---
    
    # 1. MMI Body
    # Centered at (0,0)
    mmi = c << gf.components.rectangle(size=(mmi_width, mmi_height), layer=layer)
    mmi.center = (0, 0)
    
    # 2. Top Output Arms (Taper + Straight)
    # Define reusable components
    t_top_comp = gf.components.taper(
        length=top_taper_len,
        width1=taper_top_base,
        width2=wg_width,
        layer=layer
    )
    s_top_comp = gf.components.straight(
        length=top_straight_len,
        cross_section=xs
    )
    
    # Calculate x positions centered around 0
    # For Pitch=2, N=4, offsets are: -3, -1, 1, 3
    x_offsets = [pitch * (i - (num_ports - 1) / 2) for i in range(num_ports)]
    y_top_edge = mmi_height / 2
    
    for i, x in enumerate(x_offsets):
        # Place Taper (Rotated 90 deg to point Up)
        t = c << t_top_comp
        t.rotate(90)
        t.move((x, y_top_edge))
        
        # Place Straight Extension (Connects to top of taper)
        s = c << s_top_comp
        s.rotate(90)
        s.move((x, y_top_edge + top_taper_len))
        
        # Add Port
        c.add_port(name=f"o{i+1}", port=s.ports["o2"])
        
    # 3. Bottom Input Arm
    t_bot_comp = gf.components.taper(
        length=bot_taper_len,
        width1=taper_bot_base,
        width2=wg_width,
        layer=layer
    )
    
    # Place Bottom Taper (Rotated -90 deg to point Down)
    b = c << t_bot_comp
    b.rotate(-90)
    b.move((0, -mmi_height / 2))
    
    c.add_port(name="o5", port=b.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = device_mmi_1x4_optimized()
    device.show()
    device.write_gds("mmi_1x4_optimized.gds")