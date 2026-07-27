import gdsfactory as gf

@gf.cell
def device_mzm_racetrack():
    """
    Recreates the MZM/Heater geometry inside a racetrack loop.
    Footprint target: 5.5 um x 3.0 um.
    """
    c = gf.Component()
    
    # =======================================================================
    # 1. Parameters & Dimensions
    # =======================================================================
    layer_wg = (1, 0)
    
    # Outer Racetrack Dimensions
    h_total = 3.0
    l_total = 5.5
    w_ring = 0.6
    
    # Derived ring parameters
    # Centerline radius: (Total Height - Ring Width) / 2
    # (3.0 - 0.6) / 2 = 1.2 um
    radius = (h_total - w_ring) / 2.0  
    
    # Straight length: Total Length - Total Height (for a standard stadium shape)
    # 5.5 - 3.0 = 2.5 um
    l_straight = l_total - h_total
    
    # Inner Arm Dimensions
    w_arm_thin = 0.25
    w_arm_block = 0.65
    y_arm_offset = 0.45  # Vertical position of arms from center
    
    # Block/Pad parameters
    l_block = 0.7
    l_gap = 0.25
    
    # =======================================================================
    # 2. Define Cross Sections
    # =======================================================================
    # Note: We set radius=0.01 for the inner structures to avoid ValueError 
    # because the S-bends are very tight (curvature radius < 0.1 um).
    
    xs_ring = gf.cross_section.cross_section(
        width=w_ring, 
        layer=layer_wg, 
        radius=radius
    )
    
    xs_thin = gf.cross_section.cross_section(
        width=w_arm_thin, 
        layer=layer_wg, 
        radius=0.01  # Lower limit to allow tight S-bends
    )
    
    xs_block = gf.cross_section.cross_section(
        width=w_arm_block, 
        layer=layer_wg, 
        radius=0.01
    )

    # =======================================================================
    # 3. Build Outer Racetrack
    # =======================================================================
    
    # Top Straight
    st = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    st.movex(-l_straight/2).movey(radius)
    
    # Bottom Straight
    sb = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    sb.movex(-l_straight/2).movey(-radius)
    
    # Right Bend (180 deg) - Standard Euler bend mirrored to turn right
    br = c << gf.components.bend_euler(radius=radius, angle=180, cross_section=xs_ring)
    br.mirror_y() 
    br.connect("o1", st.ports["o2"])
    
    # Left Bend (180 deg) - Closing the loop
    # Connect output of left bend (o2) to input of top straight (o1)
    bl = c << gf.components.bend_euler(radius=radius, angle=180, cross_section=xs_ring)
    bl.mirror_y()
    bl.connect("o2", st.ports["o1"]) 
    
    # =======================================================================
    # 4. Build Inner Arms
    # =======================================================================
    # Create a reusable sub-component for the straight part of the arm with blocks
    arm_c = gf.Component("inner_arm_segment")
    
    # Left Block
    b1 = arm_c << gf.components.straight(length=l_block, cross_section=xs_block)
    b1.movex(-(l_block + l_gap/2))
    
    # Center Gap
    g = arm_c << gf.components.straight(length=l_gap, cross_section=xs_thin)
    g.movex(-l_gap/2)
    
    # Right Block
    b2 = arm_c << gf.components.straight(length=l_block, cross_section=xs_block)
    b2.movex(l_gap/2)
    
    # Expose ports for the arm component
    arm_c.add_port("o1", port=b1.ports["o1"])
    arm_c.add_port("o2", port=b2.ports["o2"])
    
    # Instantiate Top and Bottom Arms
    arm_top = c << arm_c
    arm_top.movey(y_arm_offset)
    
    arm_bot = c << arm_c
    arm_bot.movey(-y_arm_offset)
    
    # =======================================================================
    # 5. Connect Arms to Ring (S-Bends)
    # =======================================================================
    # Calculate S-bend dimensions to bridge arm ends to the ring start
    dx_sb = (l_straight/2) - (l_block + l_gap/2) 
    dy_sb = radius - y_arm_offset
    
    sb_size = (dx_sb, dy_sb)
    
    # Top Right Connector
    tr = c << gf.components.bend_s(size=sb_size, cross_section=xs_thin)
    tr.connect("o1", arm_top.ports["o2"])
    
    # Top Left Connector (Mirror X)
    tl = c << gf.components.bend_s(size=sb_size, cross_section=xs_thin)
    tl.mirror_x()
    tl.connect("o1", arm_top.ports["o1"])
    
    # Bottom Right Connector (Mirror Y)
    br_conn = c << gf.components.bend_s(size=sb_size, cross_section=xs_thin)
    br_conn.mirror_y()
    br_conn.connect("o1", arm_bot.ports["o2"])
    
    # Bottom Left Connector (Mirror XY)
    bl_conn = c << gf.components.bend_s(size=sb_size, cross_section=xs_thin)
    bl_conn.mirror_y()
    bl_conn.mirror_x()
    bl_conn.connect("o1", arm_bot.ports["o1"])

    return c

if __name__ == "__main__":
    device = device_mzm_racetrack()
    device.write_gds("mzm_racetrack.gds")
    device.show()