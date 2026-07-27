import gdsfactory as gf

@gf.cell
def symmetric_directional_coupler() -> gf.Component:
    c = gf.Component("directional_coupler")
    
    # --- Refined Parameters ---
    # Increased width to match the thicker visual proportions 
    # while keeping total height at 4 um
    wg_width = 1.0  
    gap = 0.2
    
    # Refined length distribution matching total length = 120 um
    # Shorter, sharper S-bends with longer straight sections
    l_port = 20.0
    l_couple = 50.0
    dx_sbend = 15.0 
    
    # Y-axis coordinates matching total height = 4 um bounds (-2.0 to 2.0)
    y_outer_center = 2.0 - (wg_width / 2)      # 1.5
    y_inner_center = (wg_width + gap) / 2      # 0.6
    dy_sbend = y_outer_center - y_inner_center # 0.9
    
    # Cross section definition
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))
    
    # --- Primitives ---
    str_port = gf.components.straight(length=l_port, cross_section=xs)
    str_mid = gf.components.straight(length=l_couple, cross_section=xs)
    
    # S-bends
    sbend_down = gf.components.bend_s(size=(dx_sbend, -dy_sbend), cross_section=xs)
    sbend_up = gf.components.bend_s(size=(dx_sbend, dy_sbend), cross_section=xs)

    # --- Assembly: Top Arm ---
    in_t = c << str_port
    in_t.move((0, y_outer_center))
    
    sb_in_t = c << sbend_down
    sb_in_t.connect("o1", in_t.ports["o2"])
    
    mid_t = c << str_mid
    mid_t.connect("o1", sb_in_t.ports["o2"])
    
    sb_out_t = c << sbend_up
    sb_out_t.connect("o1", mid_t.ports["o2"])
    
    out_t = c << str_port
    out_t.connect("o1", sb_out_t.ports["o2"])

    # --- Assembly: Bottom Arm ---
    in_b = c << str_port
    in_b.move((0, -y_outer_center))
    
    sb_in_b = c << sbend_up
    sb_in_b.connect("o1", in_b.ports["o2"])
    
    mid_b = c << str_mid
    mid_b.connect("o1", sb_in_b.ports["o2"])
    
    sb_out_b = c << sbend_down
    sb_out_b.connect("o1", mid_b.ports["o2"])
    
    out_b = c << str_port
    out_b.connect("o1", sb_out_b.ports["o2"])

    # --- Map External Ports ---
    c.add_port("o1", port=in_t.ports["o1"])   # Top Left
    c.add_port("o2", port=in_b.ports["o1"])   # Bottom Left
    c.add_port("o3", port=out_t.ports["o2"])  # Top Right
    c.add_port("o4", port=out_b.ports["o2"])  # Bottom Right

    return c

if __name__ == "__main__":
    # Create the component
    coupler = symmetric_directional_coupler()
    
    # Save the GDS file output
    coupler.write_gds("symmetric_directional_coupler.gds")