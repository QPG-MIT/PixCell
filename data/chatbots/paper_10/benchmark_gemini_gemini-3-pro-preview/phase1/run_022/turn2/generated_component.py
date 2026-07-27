import gdsfactory as gf

@gf.cell
def reproduction_device():
    c = gf.Component("Device_Reproduction")

    # =======================================================================
    # 1. Dimensions & Constraints (Footprint: 3.0um x 5.5um)
    # =======================================================================
    h_total = 3.0
    w_total = 5.5
    
    # Feature widths
    w_ring = 0.6
    w_arm = 0.22      # Inner MZI arms are thinner
    layer_main = (1, 0)

    # Geometry Calculations
    # To fit exactly in height 3.0 with width 0.6:
    # Outer Edge = R_center + w/2 = 1.5
    # R_center = 1.5 - 0.3 = 1.2
    r_center = 1.2
    
    # Straight length to fit width 5.5:
    # Total Width = Straight + 2 * Outer_Radius
    # 5.5 = Straight + 3.0  => Straight = 2.5
    l_straight = 2.5

    # =======================================================================
    # 2. Cross Sections
    # =======================================================================
    # Explicitly define radius to avoid validation errors
    xs_ring = gf.cross_section.cross_section(
        width=w_ring, 
        layer=layer_main, 
        radius=r_center
    )
    
    # Inner arms need a very small bend radius allowed (0.1um)
    xs_arm = gf.cross_section.cross_section(
        width=w_arm, 
        layer=layer_main, 
        radius=0.1
    )

    # =======================================================================
    # 3. Build Outer Racetrack Ring
    # =======================================================================
    # We use a standard 180 degree bend.
    bend_comp = gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs_ring)
    straight_comp = gf.components.straight(length=l_straight, cross_section=xs_ring)

    # 3a. Top Straight (Placed at top center)
    st = c << straight_comp
    st.move((-l_straight/2, r_center)) # Center of waveguide is at y = 1.2

    # 3b. Right Bend (East -> South -> West)
    # Standard bend goes East -> North -> West. We need to Mirror it.
    br = c << bend_comp
    br.connect("o1", st.ports["o2"])
    br.mirror(p1=br.ports["o1"].center, p2=(br.ports["o1"].center[0]+1, br.ports["o1"].center[1]))
    # Note: mirror() mirrors across the line formed by p1-p2. 
    # Mirroring across y=constant (horizontal line) flips Vertical direction.

    # 3c. Bottom Straight (West -> East? No, Ring flow is circular)
    # Top straight: Left to Right. Right Bend: Down. 
    # Bottom straight: Right to Left.
    sb = c << straight_comp
    sb.connect("o1", br.ports["o2"])

    # 3d. Left Bend (West -> North -> East)
    # Standard bend orientation works for "Left Turn" logic, but we are connecting to a West-facing port.
    bl = c << bend_comp
    bl.connect("o1", sb.ports["o2"])
    # Standard bend o1 faces East (0). Connecting to sb.o2 (facing West/180) automatically rotates it 180.
    # Rotated 180 standard bend goes: West -> South -> East.
    # We need West -> North -> East.
    # So we MUST mirror this one as well.
    bl.mirror(p1=bl.ports["o1"].center, p2=(bl.ports["o1"].center[0]+1, bl.ports["o1"].center[1]))

    # =======================================================================
    # 4. Build Inner MZI
    # =======================================================================
    # MZI Params
    mzi_gap = 0.65       # Vertical spacing between arms
    l_arm = 1.2          # Length of straight part of arms
    l_taper = 0.5        # Length of S-bend
    
    # 4a. Anchors (Rectangles bridging the MZI to the Ring)
    anchor = gf.components.rectangle(size=(0.4, 0.6), layer=layer_main, centered=True)
    
    # Left Anchor
    anch_l = c << anchor
    anch_l.move((-l_straight/2 + 0.1, 0))

    # Right Anchor
    anch_r = c << anchor
    anch_r.move((l_straight/2 - 0.1, 0))

    # 4b. Splitters (S-bends)
    y_offset = mzi_gap / 2.0
    s_bend = gf.components.bend_s(size=(l_taper, y_offset), cross_section=xs_arm)
    
    # Instantiate Left Splitters
    ls_top = c << s_bend
    ls_bot = c << s_bend
    
    # Position at Right face of Left Anchor
    ls_top.move((anch_l.xmax, 0))
    ls_bot.move((anch_l.xmax, 0))
    ls_bot.mirror_y() # Flip bottom one to go down

    # 4c. Straight Arms
    arm_wg = gf.components.straight(length=l_arm, cross_section=xs_arm)
    
    top_arm = c << arm_wg
    bot_arm = c << arm_wg
    
    top_arm.connect("o1", ls_top.ports["o2"])
    bot_arm.connect("o1", ls_bot.ports["o2"])

    # 4d. Combiners (Right side)
    rs_top = c << s_bend
    rs_bot = c << s_bend
    
    # Connect top combiner
    rs_top.connect("o1", top_arm.ports["o2"])
    rs_top.mirror_y() # Curve down to center
    
    # Connect bottom combiner
    rs_bot.connect("o1", bot_arm.ports["o2"])
    # Default S-bend curves up, matches trajectory

    # 4e. Bridge to Right Anchor
    # Check if there is a gap between MZI end and Right Anchor
    mzi_end_x = rs_top.ports["o2"].center[0]
    if anch_r.xmin > mzi_end_x:
        bridge_len = anch_r.xmin - mzi_end_x
        # Add a small bridge block
        bridge = c << gf.components.rectangle(size=(bridge_len + 0.02, 0.4), layer=layer_main, centered=True)
        bridge.move((mzi_end_x + bridge_len/2, 0))

    # =======================================================================
    # 5. Heater Pads
    # =======================================================================
    pad_w = 0.5
    pad_h = 0.4
    pad_gap = 0.15
    
    pad = gf.components.rectangle(size=(pad_w, pad_h), layer=layer_main, centered=True)
    
    # Calculate Center Positions
    c_x = top_arm.center[0]
    y_t = top_arm.center[1]
    y_b = bot_arm.center[1]
    
    # Top Arm Pads
    p1 = c << pad
    p1.move((c_x - pad_w/2 - pad_gap/2, y_t))
    
    p2 = c << pad
    p2.move((c_x + pad_w/2 + pad_gap/2, y_t))
    
    # Bottom Arm Pads
    p3 = c << pad
    p3.move((c_x - pad_w/2 - pad_gap/2, y_b))
    
    p4 = c << pad
    p4.move((c_x + pad_w/2 + pad_gap/2, y_b))

    return c

if __name__ == "__main__":
    device = reproduction_device()
    device.show()
    device.write_gds("recreated_device_final.gds")