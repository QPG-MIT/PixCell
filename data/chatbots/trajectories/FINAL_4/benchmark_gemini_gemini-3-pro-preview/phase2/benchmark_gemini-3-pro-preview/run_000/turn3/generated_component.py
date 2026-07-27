import gdsfactory as gf

@gf.cell
def adiabatic_coupler():
    """
    Creates an adiabatic directional coupler.
    Replicates the visual geometry of the provided image with a 18um x 3um footprint.
    Includes a short interaction region and optimized width/gap for visual matching.
    """
    c = gf.Component()
    
    # 1. Define Constraints & Parameters
    length = 18.0
    total_height = 3.0
    
    # Tuned parameters for visual match:
    # - Waveguides appear thick (approx 0.85um to match the heavy black lines)
    # - Gap is very tight at waist (approx 0.15um)
    # - Interaction region is flattened (added 1.0um straight section to remove the sharp 'point' look)
    wg_width = 0.85
    gap = 0.15
    straight_len = 1.0
    
    # Calculate bend lengths
    # Total length = 2 * bend_len + straight_len
    # (18.0 - 1.0) / 2 = 8.5um per bend
    bend_len = (length - straight_len) / 2
    
    # 2. Derive Coordinates
    # We ensure the outer bounding box is exactly 3.0um tall (+1.5 to -1.5)
    
    # Y-coordinates at Input/Output (Widest separation)
    # Top Arm Start Center: Top Edge (1.5) - Half Width
    y_top_start = (total_height / 2) - (wg_width / 2)  
    
    # Y-coordinates at Waist (Narrowest separation)
    # Top Arm Waist Center: Half Gap + Half Width
    y_top_waist = (gap / 2) + (wg_width / 2)
    
    # Displacements
    # Top arm moves DOWN from start to waist
    dy_top_in = y_top_waist - y_top_start
    # Top arm moves UP from waist to end
    dy_top_out = -dy_top_in
    
    # Bottom arm is symmetric (mirror of top)
    y_bot_start = -y_top_start
    y_bot_waist = -y_top_waist
    dy_bot_in = y_bot_waist - y_bot_start
    dy_bot_out = -dy_bot_in
    
    # Cross-section
    xs = gf.cross_section.cross_section(width=wg_width)

    # 3. Construct Geometry
    
    # --- Top Arm ---
    # Converging S-bend (Input -> Waist)
    t_in = c << gf.components.bend_s(size=(bend_len, dy_top_in), cross_section=xs)
    t_in.movey(y_top_start)
    
    # Straight Interaction Section (Waist)
    t_mid = c << gf.components.straight(length=straight_len, cross_section=xs)
    t_mid.connect("o1", t_in.ports["o2"])
    
    # Diverging S-bend (Waist -> Output)
    t_out = c << gf.components.bend_s(size=(bend_len, dy_top_out), cross_section=xs)
    t_out.connect("o1", t_mid.ports["o2"])
    
    # --- Bottom Arm ---
    # Converging S-bend
    b_in = c << gf.components.bend_s(size=(bend_len, dy_bot_in), cross_section=xs)
    b_in.movey(y_bot_start)
    
    # Straight Interaction Section
    b_mid = c << gf.components.straight(length=straight_len, cross_section=xs)
    b_mid.connect("o1", b_in.ports["o2"])
    
    # Diverging S-bend
    b_out = c << gf.components.bend_s(size=(bend_len, dy_bot_out), cross_section=xs)
    b_out.connect("o1", b_mid.ports["o2"])
    
    # 4. Expose Ports
    c.add_port("o1", port=t_in.ports["o1"])   # Top Left
    c.add_port("o2", port=b_in.ports["o1"])   # Bottom Left
    c.add_port("o3", port=t_out.ports["o2"])  # Top Right
    c.add_port("o4", port=b_out.ports["o2"])  # Bottom Right

    return c

if __name__ == "__main__":
    device = adiabatic_coupler()
    device.write_gds("adiabatic_coupler.gds")
    device.show()