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
    
    # Waveguide width kept at 0.6 to match visual density
    wg_width = 0.6
    
    # Gap increased to 0.5um based on visual inspection of the target
    # where the gap at the waist is roughly comparable to the waveguide width
    # (previous gap of 0.2 was too tight).
    gap_min = 0.5  
    
    # Increased coupling length to 4.0um to create the distinct 
    # extended parallel "waist" region seen in the target image.
    coupling_length = 4.0
    
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
    y_inner = (gap_min / 2.0) + (wg_width / 2.0)
    
    # Vertical displacement (dy) for the S-bends
    # Top arm input goes from y_outer down to y_inner.
    # Since y_inner < y_outer, dy is negative.
    dy = y_inner - y_outer
    
    # Define cross section
    xs = gf.cross_section.cross_section(width=wg_width)

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
    # Start Y is -y_outer. Target Y is -y_inner.
    # Delta Y = -y_inner - (-y_outer) = y_outer - y_inner = -dy (positive move)
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