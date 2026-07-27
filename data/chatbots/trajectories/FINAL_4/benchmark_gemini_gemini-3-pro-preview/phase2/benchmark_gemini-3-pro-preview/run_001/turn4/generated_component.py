import gdsfactory as gf

@gf.cell
def directional_coupler_18x3():
    c = gf.Component()

    # =============================================================
    # Geometry Parameters
    # Total Footprint: 18.0 x 3.0 um
    # =============================================================
    total_length = 18.0
    total_height = 3.0
    
    # Waveguide width increased to 0.6 to better match the visual density 
    # of the black lines in the target image relative to the gap.
    wg_width = 0.6
    gap_min = 0.2  # Minimum gap at the center
    
    # Introduce a straight coupling section to replicate the 'flat' waist
    # observed in the target, rather than a single point of closest approach.
    coupling_length = 1.6
    
    # The remaining length is split between the input and output S-bends
    sbend_length = (total_length - coupling_length) / 2.0
    
    # =============================================================
    # Coordinate Calculations
    # =============================================================
    # Outer Y position (at ports):
    # To fit strictly within 3.0um height, we position the outer edges at +/- 1.5.
    # Center y = 1.5 - (width/2)
    y_outer = (total_height / 2.0) - (wg_width / 2.0)
    
    # Inner Y position (at center waist):
    # Center y = (gap/2) + (width/2)
    y_inner = (gap_min + wg_width) / 2.0
    
    # Vertical displacement (dy) for the S-bends
    # Top arm input goes from y_outer down to y_inner.
    dy = y_inner - y_outer
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=wg_width, radius=5.0)

    # =============================================================
    # Top Arm Construction
    # =============================================================
    # 1. Input S-bend (Converging)
    sb_in_top = c << gf.components.bend_s(size=(sbend_length, dy), cross_section=xs)
    sb_in_top.move((-total_length/2.0, y_outer)) # Start at left edge
    
    # 2. Straight Coupling Section
    st_top = c << gf.components.straight(length=coupling_length, cross_section=xs)
    st_top.connect("o1", sb_in_top.ports["o2"])
    
    # 3. Output S-bend (Diverging)
    # Displacement is -dy (moving back up)
    sb_out_top = c << gf.components.bend_s(size=(sbend_length, -dy), cross_section=xs)
    sb_out_top.connect("o1", st_top.ports["o2"])

    # =============================================================
    # Bottom Arm Construction
    # =============================================================
    # 1. Input S-bend (Converging)
    # Displacement is -dy (moving up from bottom)
    sb_in_bot = c << gf.components.bend_s(size=(sbend_length, -dy), cross_section=xs)
    sb_in_bot.move((-total_length/2.0, -y_outer))
    
    # 2. Straight Coupling Section
    st_bot = c << gf.components.straight(length=coupling_length, cross_section=xs)
    st_bot.connect("o1", sb_in_bot.ports["o2"])
    
    # 3. Output S-bend (Diverging)
    # Displacement is dy (moving back down)
    sb_out_bot = c << gf.components.bend_s(size=(sbend_length, dy), cross_section=xs)
    sb_out_bot.connect("o1", st_bot.ports["o2"])

    # =============================================================
    # Expose Ports
    # =============================================================
    c.add_port("o1", port=sb_in_top.ports["o1"])
    c.add_port("o2", port=sb_in_bot.ports["o1"])
    c.add_port("o3", port=sb_out_top.ports["o2"])
    c.add_port("o4", port=sb_out_bot.ports["o2"])

    return c

# Create and save the device
device = directional_coupler_18x3()
device.write_gds("directional_coupler_18x3.gds")