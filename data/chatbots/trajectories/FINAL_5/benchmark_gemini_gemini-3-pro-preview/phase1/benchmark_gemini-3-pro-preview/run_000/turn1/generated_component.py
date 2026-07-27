import gdsfactory as gf

@gf.cell
def device_coupler_compact():
    """
    Recreates the compact grating-assisted directional coupler loop device.
    Footprint constraint: 18.24 um x 0.7 um.
    """
    c = gf.Component()
    
    # =======================================================================
    # Parameters
    # =======================================================================
    # Dimensions (fine-tuned for compact footprint)
    w_bus = 0.06        # Central bus width
    w_grating = 0.07    # Segmented waveguide width
    w_outer = 0.08      # Outer solid arm width
    
    gap_coupling = 0.05 # Gap between bus and grating
    gap_loop = 0.06     # Gap between grating and outer arm
    
    # Grating Parameters
    pitch = 0.16
    duty_cycle = 0.5
    N_periods = 45
    L_grating = N_periods * pitch
    
    # Vertical positions (Center y = 0)
    # y positions for the grating layer (top and bottom)
    y_g_top = (w_bus / 2) + gap_coupling + (w_grating / 2)
    y_g_bot = -y_g_top
    
    # y positions for the outer return arms
    y_o_top = y_g_top + (w_grating / 2) + gap_loop + (w_outer / 2)
    y_o_bot = -y_o_top
    
    # Bend Calculation
    # The 180-degree bend connects the grating layer to the outer layer.
    bend_radius = (y_o_top - y_g_top) / 2  # Approx 0.0675 um
    
    # Horizontal positions
    # Align the U-bend (right side) to x = 8.0
    x_bend = 8.0
    x_g_end = x_bend
    x_g_start = x_g_end - L_grating
    
    # Taper tips on the far left
    x_tip_left = -9.0
    L_taper = 1.5
    x_arm_straight_start = x_tip_left + L_taper

    # =======================================================================
    # Custom Cross-Sections (To Bypass Radius Checks)
    # =======================================================================
    # We define cross-sections with radius_min=0.0 to allow nanophotonic bends.
    
    xs_outer = gf.cross_section.cross_section(
        width=w_outer, 
        layer=(1, 0), 
        radius_min=0.0
    )
    
    xs_grating = gf.cross_section.cross_section(
        width=w_grating, 
        layer=(1, 0), 
        radius_min=0.0
    )

    # =======================================================================
    # Geometry Construction
    # =======================================================================

    # 1. Central Bus Waveguide
    # Runs the full length of the active region plus margin
    L_bus = (x_bend + 0.5) - x_tip_left
    bus = c << gf.components.straight(length=L_bus, width=w_bus)
    bus.move((x_tip_left, -w_bus/2))

    # 2. Grating Waveguides (Top and Bottom)
    segment_len = pitch * duty_cycle
    # Create the single grating tooth component
    rect = gf.components.rectangle(size=(segment_len, w_grating), layer=(1,0), centered=True)
    
    # Calculate start position for array (center of first element)
    x_first_center = x_g_start + segment_len/2
    
    # Top Grating Loop
    for i in range(N_periods):
        ref = c << rect
        ref.move((x_first_center + i * pitch, y_g_top))
    
    # Bottom Grating Loop
    for i in range(N_periods):
        ref = c << rect
        ref.move((x_first_center + i * pitch, y_g_bot))

    # 3. 180 Degree Bends (Right Side)
    # Top Bend: Connects grating layer (upwards) to outer layer.
    # Passing cross_section=xs_outer allows the tiny radius.
    b_top = c << gf.components.bend_circular(
        radius=bend_radius, 
        angle=180, 
        cross_section=xs_outer
    )
    b_top.move((x_bend, y_g_top))
    
    # Bottom Bend
    b_bot = c << gf.components.bend_circular(
        radius=bend_radius, 
        angle=180, 
        cross_section=xs_outer
    )
    b_bot.mirror(p1=(0,0), p2=(1,0)) # Mirror vertically
    b_bot.move((x_bend, y_g_bot))

    # 4. Outer Solid Arms (Left Side)
    # Connects from the bend output back to the left taper
    L_arm = x_bend - x_arm_straight_start
    
    # Top Arm
    arm_top = c << gf.components.straight(length=L_arm, width=w_outer)
    arm_top.connect("o2", b_top.ports["o2"])
    
    taper_top = c << gf.components.taper(length=L_taper, width1=0.01, width2=w_outer)
    taper_top.connect("o2", arm_top.ports["o1"])
    
    # Bottom Arm
    arm_bot = c << gf.components.straight(length=L_arm, width=w_outer)
    arm_bot.connect("o2", b_bot.ports["o2"])
    
    taper_bot = c << gf.components.taper(length=L_taper, width1=0.01, width2=w_outer)
    taper_bot.connect("o2", arm_bot.ports["o1"])

    # 5. Input Coupling Ports (Curved Tails)
    # Attached to the left start of the grating section, flaring outwards.
    # Radius=2.0 is also often < default 5.0, so we use xs_grating.
    
    # Top Input (Curves Up-Left)
    bend_in_top = c << gf.components.bend_euler(
        radius=2.0, 
        angle=25, 
        cross_section=xs_grating
    )
    bend_in_top.mirror(p1=(0,0), p2=(0,1)) # Flip X axis (points West)
    bend_in_top.move((x_g_start, y_g_top)) # Place at start of grating
    
    taper_in_top = c << gf.components.taper(length=0.5, width1=0.01, width2=w_grating)
    taper_in_top.connect("o2", bend_in_top.ports["o2"])
    
    # Bottom Input (Curves Down-Left)
    bend_in_bot = c << gf.components.bend_euler(
        radius=2.0, 
        angle=25, 
        cross_section=xs_grating
    )
    bend_in_bot.mirror(p1=(0,0), p2=(0,1)) # Flip X
    bend_in_bot.mirror(p1=(0,0), p2=(1,0)) # Flip Y
    bend_in_bot.move((x_g_start, y_g_bot))
    
    taper_in_bot = c << gf.components.taper(length=0.5, width1=0.01, width2=w_grating)
    taper_in_bot.connect("o2", bend_in_bot.ports["o2"])

    return c

if __name__ == "__main__":
    device = device_coupler_compact()
    device.write_gds("compact_coupler_fixed.gds")