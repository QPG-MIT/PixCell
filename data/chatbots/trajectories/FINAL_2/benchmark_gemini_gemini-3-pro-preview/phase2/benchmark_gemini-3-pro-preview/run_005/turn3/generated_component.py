import gdsfactory as gf

@gf.cell
def device_mmi_1x4_optimized():
    """
    1x4 MMI Power Splitter
    
    Dimensions optimized to match target image visual proportions and [25, 10] footprint.
    Interpreting footprint [25, 10] as Height=25um, Width=10um based on the vertical nature of the device.
    
    Geometric breakdown:
    - Total Height: 25.0um
    - Total Width: 10.0um (defined by MMI block)
    - MMI Body: 10.0um x 6.0um (Landscape aspect ratio matches target)
    - Top Fingers: 4x, pitch 2.0um. Split into Taper (7.5um) + Straight (8.0um).
    - Bottom Finger: 1x, centered. Short wide taper (3.5um).
    """
    c = gf.Component()
    
    # Layer definition
    layer = (1, 0)
    
    # --- Dimensions ---
    
    # Main Body
    mmi_width = 10.0
    mmi_height = 6.0
    
    # Vertical Constraints (Total = 25.0)
    bot_taper_len = 3.5
    top_taper_len = 7.5
    # Remaining budget for straights: 25.0 - (6.0 + 3.5 + 7.5) = 8.0
    top_straight_len = 8.0
    
    # Widths
    wg_width = 0.6
    taper_top_base = 1.4  # Creates ~0.6um gap with 2.0 pitch
    taper_bot_base = 2.4  # Wide input taper
    
    # Spacing
    pitch = 2.0
    num_ports = 4
    
    # Cross Section for straights
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # --- Primitives ---
    
    # 1. MMI Body (Rectangle)
    mmi = c << gf.components.rectangle(size=(mmi_width, mmi_height), layer=layer)
    # Center the MMI at (0,0) for easier relative placement
    mmi.center = (0, 0)
    
    # 2. Top Output Fingers
    # We define reusable components for the taper and straight sections
    taper_top_comp = gf.components.taper(
        length=top_taper_len,
        width1=taper_top_base,
        width2=wg_width,
        layer=layer
    )
    straight_top_comp = gf.components.straight(
        length=top_straight_len,
        cross_section=xs
    )
    
    # Calculate x-offsets for 4 ports centered around 0
    # Formula: pitch * (i - (N-1)/2) -> for N=4, pitch=2: -3, -1, 1, 3
    x_offsets = [pitch * (i - (num_ports - 1) / 2) for i in range(num_ports)]
    y_top_edge = mmi_height / 2
    
    for i, x in enumerate(x_offsets):
        # Place Taper
        # Rotate 90 so it points Up (+y). 
        # width1 (base) is at (0,0), width2 (tip) at (0, L)
        t = c << taper_top_comp
        t.rotate(90)
        t.move((x, y_top_edge))
        
        # Place Straight Extension
        # Connects to the end of the taper
        s = c << straight_top_comp
        s.rotate(90)
        s.move((x, y_top_edge + top_taper_len))
        
        # Expose Port
        c.add_port(name=f"o{i+1}", port=s.ports["o2"])

    # 3. Bottom Input Finger
    taper_bot_comp = gf.components.taper(
        length=bot_taper_len,
        width1=taper_bot_base,
        width2=wg_width,
        layer=layer
    )
    
    b = c << taper_bot_comp
    b.rotate(-90) # Points Down (-y). width1 at (0,0), width2 at (0, -L)
    b.move((0, -mmi_height / 2))
    
    c.add_port(name="o5", port=b.ports["o2"])
    
    return c

if __name__ == "__main__":
    device = device_mmi_1x4_optimized()
    device.show()
    device.write_gds("mmi_1x4_optimized.gds")