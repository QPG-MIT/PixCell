import gdsfactory as gf

@gf.cell
def directional_coupler():
    """
    Creates a symmetric directional coupler built from basic parametric primitives.
    Strictly constrained to a [120, 4] footprint constraint.
    """
    c = gf.Component("directional_coupler")
    
    # 1. Define waveguide cross-section (Increased width to match target visual thickness)
    wg_width = 0.8
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 2. Footprint Constraints & Parameters
    total_length = 120.0
    total_height = 4.0
    gap = 0.15  # Tighter gap to match the thin sliver in the target image
    
    # Section horizontal lengths (Total = 15 + 15 + 60 + 15 + 15 = 120)
    L_port = 15.0
    dx_sbend = 15.0
    L_center = 60.0

    # 3. Calculate exact Y positions to satisfy the exactly 4um total height
    # Total height is 4.0, assuming centered at Y=0 -> Bounding box outer limits are +/- 2.0
    # Port waveguide centers Y coordinates (outer edges perfectly touch +/- 2.0)
    y_port_top = (total_height / 2) - (wg_width / 2)    #  1.6
    y_port_bot = -(total_height / 2) + (wg_width / 2)   # -1.6

    # Central coupling region waveguide centers Y coordinates
    y_center_top = (gap / 2) + (wg_width / 2)           #  0.475
    y_center_bot = -(gap / 2) - (wg_width / 2)          # -0.475

    # Calculate the Y transition distances (dy) for the S-bends
    dy_top_in = y_center_top - y_port_top   # -1.125 (Moves down into the gap)
    dy_top_out = y_port_top - y_center_top  #  1.125 (Moves up to outer port)
    dy_bot_in = y_center_bot - y_port_bot   #  1.125 (Moves up into the gap)
    dy_bot_out = y_port_bot - y_center_bot  # -1.125 (Moves down to outer port)

    # 4. Generate Primitives
    straight_center = gf.components.straight(length=L_center, cross_section=xs)
    straight_port = gf.components.straight(length=L_port, cross_section=xs)

    b_top_in = gf.components.bend_s(size=(dx_sbend, dy_top_in), cross_section=xs)
    b_top_out = gf.components.bend_s(size=(dx_sbend, dy_top_out), cross_section=xs)
    b_bot_in = gf.components.bend_s(size=(dx_sbend, dy_bot_in), cross_section=xs)
    b_bot_out = gf.components.bend_s(size=(dx_sbend, dy_bot_out), cross_section=xs)

    # 5. Instantiate and Position Center Waveguides
    st_top_ref = c << straight_center
    st_bot_ref = c << straight_center
    
    # Placing the starting port (o1) of the central waveguides at correct horizontal offset
    st_top_ref.move((L_port + dx_sbend, y_center_top))
    st_bot_ref.move((L_port + dx_sbend, y_center_bot))

    # 6. Instantiate & Auto-Connect S-Bends directly to central guides
    sb_top_in_ref = c << b_top_in
    sb_top_in_ref.connect("o2", st_top_ref.ports["o1"])

    sb_top_out_ref = c << b_top_out
    sb_top_out_ref.connect("o1", st_top_ref.ports["o2"])

    sb_bot_in_ref = c << b_bot_in
    sb_bot_in_ref.connect("o2", st_bot_ref.ports["o1"])

    sb_bot_out_ref = c << b_bot_out
    sb_bot_out_ref.connect("o1", st_bot_ref.ports["o2"])

    # 7. Instantiate & Auto-Connect Input/Output straights to finish footprint
    port_top_in = c << straight_port
    port_top_in.connect("o2", sb_top_in_ref.ports["o1"])

    port_top_out = c << straight_port
    port_top_out.connect("o1", sb_top_out_ref.ports["o2"])

    port_bot_in = c << straight_port
    port_bot_in.connect("o2", sb_bot_in_ref.ports["o1"])

    port_bot_out = c << straight_port
    port_bot_out.connect("o1", sb_bot_out_ref.ports["o2"])

    # 8. Expose standard component ports
    c.add_port("o1", port=port_top_in.ports["o1"])
    c.add_port("o2", port=port_bot_in.ports["o1"])
    c.add_port("o3", port=port_top_out.ports["o2"])
    c.add_port("o4", port=port_bot_out.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component
    device = directional_coupler()
    
    # Write the GDS file out to disk
    device.write_gds("directional_coupler_adjusted.gds")