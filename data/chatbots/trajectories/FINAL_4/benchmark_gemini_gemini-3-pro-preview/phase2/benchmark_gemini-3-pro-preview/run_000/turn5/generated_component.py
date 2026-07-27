import gdsfactory as gf

@gf.cell
def adiabatic_coupler():
    """
    Creates an adiabatic directional coupler matching the visual constraints.
    Footprint: 18um x 3um.
    Features:
    - Waveguide width increased to 1.0um to match the 1:1 gap-to-width ratio at input.
    - Extended central straight section (4.0um) for a longer interaction region.
    - Smooth S-bend transitions using gentle offsets.
    """
    c = gf.Component()
    
    # 1. Geometry Constraints & Parameters
    length = 18.0
    total_height = 3.0
    
    # Tuned parameters for visual match:
    # Width increased to 1.0 to fill the vertical space more (bold look).
    # Gap kept small (0.2) for the waist.
    # Straight length increased to 4.0 to match the elongated parallel region.
    wg_width = 1.0
    gap = 0.2
    straight_len = 4.0
    
    # Calculate bend lengths
    # The total length is composed of: Bend_In + Straight + Bend_Out
    bend_len = (length - straight_len) / 2
    
    # 2. Derive Coordinates
    # We ensure the outer edges of the waveguides touch the 3.0um bounding box limits.
    
    # Y-coordinates at Input (Widest separation)
    # Top Arm Center: Top Edge (1.5) - Half Width (0.5) = 1.0
    y_top_in = (total_height / 2) - (wg_width / 2)
    
    # Y-coordinates at Waist (Narrowest separation)
    # Top Arm Center: Half Gap (0.1) + Half Width (0.5) = 0.6
    y_top_waist = (gap / 2) + (wg_width / 2)
    
    # Displacements for S-bends
    # Top arm moves DOWN from input to waist
    dy_top_in = y_top_waist - y_top_in
    # Top arm moves UP from waist to output
    dy_top_out = -dy_top_in
    
    # Bottom arm is symmetric (mirror of top)
    y_bot_in = -y_top_in
    y_bot_waist = -y_top_waist
    dy_bot_in = y_bot_waist - y_bot_in
    dy_bot_out = -dy_bot_in
    
    # Cross-section definition
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 3. Construct Geometry
    
    # --- Top Arm ---
    # Converging S-bend (Input -> Waist)
    t_in = c << gf.components.bend_s(size=(bend_len, dy_top_in), cross_section=xs)
    t_in.movey(y_top_in)
    
    # Straight Interaction Section (Waist)
    t_mid = c << gf.components.straight(length=straight_len, cross_section=xs)
    t_mid.connect("o1", t_in.ports["o2"])
    
    # Diverging S-bend (Waist -> Output)
    t_out = c << gf.components.bend_s(size=(bend_len, dy_top_out), cross_section=xs)
    t_out.connect("o1", t_mid.ports["o2"])
    
    # --- Bottom Arm ---
    # Converging S-bend (Input -> Waist)
    b_in = c << gf.components.bend_s(size=(bend_len, dy_bot_in), cross_section=xs)
    b_in.movey(y_bot_in)
    
    # Straight Interaction Section
    b_mid = c << gf.components.straight(length=straight_len, cross_section=xs)
    b_mid.connect("o1", b_in.ports["o2"])
    
    # Diverging S-bend (Waist -> Output)
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