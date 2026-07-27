import gdsfactory as gf

@gf.cell
def directional_coupler():
    c = gf.Component("directional_coupler_smooth")
    
    # --- Dimensions & Footprint Constraints ---
    # Total footprint must strictly be 120.0 x 4.0
    L_total = 120.0
    H_total = 4.0
    
    # Waveguide and gap parameters
    wg_width = 0.5
    port_width = 1.0  # Flared ends to match the original image's tapers
    gap = 0.2
    
    # --- Structural Calculations ---
    # Calculate Y coordinates to perfectly hit the 4.0um bounding box height
    # Max Y = port_y + (port_width / 2). For Max Y = 2.0, port_y = 1.5
    y_port = (H_total - port_width) / 2.0  
    
    # Coupling region centers. Gap is between inner edges.
    y_couple = (gap + wg_width) / 2.0      # 0.35
    
    # S-bend vertical displacement
    dy = y_port - y_couple                 # 1.15
    
    # X length distribution to strictly sum up to 120.0
    L_taper = 10.0
    L_str = 10.0
    L_sbend = 20.0
    L_couple = L_total - 2 * (L_taper + L_str + L_sbend) # 120 - 80 = 40.0
    
    # --- Primitives ---
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # Input/Output Tapers
    t_in = gf.components.taper(length=L_taper, width1=port_width, width2=wg_width)
    t_out = gf.components.taper(length=L_taper, width1=wg_width, width2=port_width)
    
    # Straight sections
    str_arm = gf.components.straight(length=L_str, cross_section=xs)
    str_c = gf.components.straight(length=L_couple, cross_section=xs)
    
    # Smoothed S-bends
    sb_down = gf.components.bend_s(size=(L_sbend, -dy), cross_section=xs)
    sb_up = gf.components.bend_s(size=(L_sbend, dy), cross_section=xs)
    
    # --- Assemble Top Arm ---
    top_in = c << t_in
    top_in.move((0, y_port))
    
    top_s1 = c << str_arm
    top_s1.connect("o1", top_in.ports["o2"])
    
    top_sb1 = c << sb_down
    top_sb1.connect("o1", top_s1.ports["o2"])
    
    top_c = c << str_c
    top_c.connect("o1", top_sb1.ports["o2"])
    
    top_sb2 = c << sb_up
    top_sb2.connect("o1", top_c.ports["o2"])
    
    top_s2 = c << str_arm
    top_s2.connect("o1", top_sb2.ports["o2"])
    
    top_out = c << t_out
    top_out.connect("o1", top_s2.ports["o2"])
    
    # --- Assemble Bottom Arm ---
    bot_in = c << t_in
    bot_in.move((0, -y_port))
    
    bot_s1 = c << str_arm
    bot_s1.connect("o1", bot_in.ports["o2"])
    
    bot_sb1 = c << sb_up
    bot_sb1.connect("o1", bot_s1.ports["o2"])
    
    bot_c = c << str_c
    bot_c.connect("o1", bot_sb1.ports["o2"])
    
    bot_sb2 = c << sb_down
    bot_sb2.connect("o1", bot_c.ports["o2"])
    
    bot_s2 = c << str_arm
    bot_s2.connect("o1", bot_sb2.ports["o2"])
    
    bot_out = c << t_out
    bot_out.connect("o1", bot_s2.ports["o2"])
    
    # --- Expose External Ports ---
    c.add_port("o1", port=top_in.ports["o1"])
    c.add_port("o2", port=bot_in.ports["o1"])
    c.add_port("o3", port=top_out.ports["o2"])
    c.add_port("o4", port=bot_out.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Render and output to file
    device = directional_coupler()
    device.write_gds("directional_coupler.gds")