import gdsfactory as gf

@gf.cell
def device_mmi_1x4_improved():
    """
    1x4 MMI Power Splitter
    
    Refined dimensions to match the visual aspect ratio of the target image
    within the [25, 10] footprint constraint.
    
    Adjustments from previous iteration:
    - Reduced top straight length significantly (8.0 -> 3.0) to fix elongation.
    - Reduced top taper length (7.5 -> 6.0) to balance with MMI body.
    - Increased MMI height (6.0 -> 8.0) to match the visual 'weight' of the block.
    - Tuned taper widths for better visual gap matching.
    """
    c = gf.Component()
    
    # Layer definition
    layer = (1, 0)
    
    # --- Dimensions ---
    # Width fixed at 10.0um to match the MMI width visual and constraints
    mmi_width = 10.0
    
    # MMI Body Height
    # Target image shows a robust rectangular block
    mmi_height = 8.0
    
    # Top Section Dimensions (Output)
    # Combined length is now 9.0um (vs 15.5um previously)
    top_taper_len = 6.0 
    top_straight_len = 3.0
    
    # Bottom Section Dimensions (Input)
    bot_taper_len = 3.5
    
    # Widths
    wg_width = 0.5         # Standard single mode width
    taper_top_base = 1.6   # Wide base creates small gaps between ports (Pitch 2.0 - 1.6 = 0.4 gap)
    taper_bot_base = 2.2   # Wider input taper base
    
    # Configuration
    pitch = 2.0
    num_ports = 4
    
    # Cross Section for straight waveguides
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # --- Geometry Construction ---
    
    # 1. MMI Body
    # Centered at (0,0) for symmetry
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
    
    # Calculate x positions: centered array
    # For N=4, Pitch=2: -3, -1, 1, 3
    x_offsets = [pitch * (i - (num_ports - 1) / 2) for i in range(num_ports)]
    y_top_edge = mmi_height / 2
    
    for i, x in enumerate(x_offsets):
        # Place Taper
        # Default taper is along x-axis. Rotate 90 to point +y.
        t = c << t_top_comp
        t.rotate(90)
        t.move((x, y_top_edge))
        
        # Place Straight Extension
        # Connects to the tip of the taper
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
    
    # Place Bottom Taper
    # Rotate -90 to point -y.
    b = c << t_bot_comp
    b.rotate(-90)
    b.move((0, -mmi_height / 2))
    
    c.add_port(name="o5", port=b.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = device_mmi_1x4_improved()
    device.show()
    device.write_gds("mmi_1x4_improved.gds")