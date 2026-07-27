import gdsfactory as gf

@gf.cell
def device_mzi_racetrack():
    """
    Recreation of the 'Chain Link' MZI device.
    Footprint constraint: 3um x 5.5um
    
    Fixes: 
    1. Added Tapers to resolve PortWidthMismatchError.
    2. Set radius_min=0.1 in cross_section to resolve ValueError regarding bend radius.
    """
    c = gf.Component("chain_link_mzi")
    
    # =======================================================================
    # 1. Parameter Definition
    # =======================================================================
    # Geometry dimensions
    total_width = 5.5
    total_height = 3.0
    
    # Outer Ring parameters
    ring_width = 0.8
    r_outer = total_height / 2  # 1.5
    r_center = r_outer - (ring_width / 2) # 1.1
    l_straight_ring = total_width - (2 * r_outer) # 2.5
    
    # Inner Arm parameters
    arm_y_offset = 0.45
    arm_width = 0.25    # Narrow waveguide width
    pad_width = 0.65    # Wide heater/pad width
    
    # Segment Lengths
    pad_block_length = 0.65 
    taper_length = 0.15              
    pad_straight_length = pad_block_length - (2 * taper_length)
    
    gap_length = 0.2    # Gap between the two pad blocks
    sbend_length = 0.6  # Length of the S-bend transition to the ring
    
    # Layer definition
    lay = (1, 0)
    
    # Define Cross Sections
    # CRITICAL FIX: Set radius_min=0.1 to allow tight S-bends without error
    xs_ring = gf.cross_section.cross_section(width=ring_width, layer=lay, radius_min=0.1)
    xs_arm = gf.cross_section.cross_section(width=arm_width, layer=lay, radius_min=0.1)
    xs_pad = gf.cross_section.cross_section(width=pad_width, layer=lay, radius_min=0.1)

    # =======================================================================
    # 2. Build Outer Racetrack Ring
    # =======================================================================
    path = gf.Path()
    path.append(gf.path.straight(length=l_straight_ring))
    path.append(gf.path.arc(radius=r_center, angle=-180)) # Clockwise
    path.append(gf.path.straight(length=l_straight_ring))
    path.append(gf.path.arc(radius=r_center, angle=-180))
    
    ring = c << gf.path.extrude(path, cross_section=xs_ring)
    ring.move((-l_straight_ring / 2, r_center))

    # =======================================================================
    # 3. Build Inner MZI Arms (With Tapers)
    # =======================================================================
    
    def create_arm_segment():
        """
        Creates one arm: Input -> Taper -> Pad -> Taper -> Gap -> Taper -> Pad -> Taper -> Output
        """
        cmp = gf.Component()
        
        # --- Block 1 ---
        t1 = cmp << gf.components.taper(length=taper_length, width1=arm_width, width2=pad_width, layer=lay)
        p1 = cmp << gf.components.straight(length=pad_straight_length, cross_section=xs_pad)
        t2 = cmp << gf.components.taper(length=taper_length, width1=pad_width, width2=arm_width, layer=lay)
        
        # --- Center Gap ---
        g1 = cmp << gf.components.straight(length=gap_length, cross_section=xs_arm)
        
        # --- Block 2 ---
        t3 = cmp << gf.components.taper(length=taper_length, width1=arm_width, width2=pad_width, layer=lay)
        p2 = cmp << gf.components.straight(length=pad_straight_length, cross_section=xs_pad)
        t4 = cmp << gf.components.taper(length=taper_length, width1=pad_width, width2=arm_width, layer=lay)
        
        # Connect sequence
        p1.connect("o1", t1.ports["o2"])
        t2.connect("o1", p1.ports["o2"])
        g1.connect("o1", t2.ports["o2"])
        t3.connect("o1", g1.ports["o2"])
        p2.connect("o1", t3.ports["o2"])
        t4.connect("o1", p2.ports["o2"])
        
        cmp.add_port("o1", port=t1.ports["o1"])
        cmp.add_port("o2", port=t4.ports["o2"])
        return cmp

    # Instantiate arms
    arm_proto = create_arm_segment()
    top_arm = c << arm_proto
    bot_arm = c << arm_proto

    # Position Arms
    arm_x_center = arm_proto.xsize / 2
    top_arm.move(( -arm_x_center, arm_y_offset ))
    bot_arm.move(( -arm_x_center, -arm_y_offset ))

    # =======================================================================
    # 4. Connect Arms to Ring (S-Bends)
    # =======================================================================
    
    # --- Top Arm S-Bends ---
    # Left: S-bend from center to top arm
    sb_tl = c << gf.components.bend_s(size=(sbend_length, arm_y_offset), cross_section=xs_arm)
    sb_tl.connect("o2", top_arm.ports["o1"])
    
    # Right: S-bend from top arm to center
    sb_tr = c << gf.components.bend_s(size=(sbend_length, -arm_y_offset), cross_section=xs_arm)
    sb_tr.connect("o1", top_arm.ports["o2"])

    # --- Bottom Arm S-Bends ---
    # Left: S-bend from center to bottom arm
    sb_bl = c << gf.components.bend_s(size=(sbend_length, -arm_y_offset), cross_section=xs_arm)
    sb_bl.connect("o2", bot_arm.ports["o1"])
    
    # Right: S-bend from bottom arm to center
    sb_br = c << gf.components.bend_s(size=(sbend_length, arm_y_offset), cross_section=xs_arm)
    sb_br.connect("o1", bot_arm.ports["o2"])

    # =======================================================================
    # 5. Anchor Blocks
    # =======================================================================
    # Fill gap from S-bend start to inner ring wall
    x_inner_wall_left = -(l_straight_ring/2) - r_center + (ring_width/2)
    x_sb_start = sb_tl.ports["o1"].center[0]
    
    anchor_len = abs(x_sb_start - x_inner_wall_left) + 0.1 # overlap
    
    if anchor_len > 0:
        anc_l = c << gf.components.straight(length=anchor_len, cross_section=xs_arm)
        anc_l.connect("o1", sb_tl.ports["o1"])
        
        anc_r = c << gf.components.straight(length=anchor_len, cross_section=xs_arm)
        anc_r.connect("o1", sb_tr.ports["o2"])

    # =======================================================================
    # 6. Final Ports
    # =======================================================================
    c.add_port("o1", center=(-total_width/2, 0), width=ring_width, orientation=180, layer=lay)
    c.add_port("o2", center=(total_width/2, 0), width=ring_width, orientation=0, layer=lay)

    return c

if __name__ == "__main__":
    device = device_mzi_racetrack()
    device.write_gds("chain_link_mzi.gds")