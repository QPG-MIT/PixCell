import gdsfactory as gf

@gf.cell
def racetrack_resonator_final():
    """
    Recreation of the racetrack device based on the provided image and footprint.
    Footprint: 3um x 5.5um.
    Structure: Closed loop with modulated width on straight sections.
    """
    c = gf.Component()

    # --- 1. Dimensions & Parameters ---
    # Target Footprint: 3.0 um (H) x 5.5 um (W)
    
    w_wide = 0.8        # Width of bends and taper ends
    w_narrow = 0.2      # Width of narrow straight sections
    w_block = 0.6       # Width of rectangular pads
    
    # Layer definition
    layer = (1, 0)
    
    # Geometry Calculations
    # Height = 2*Radius + w_wide  =>  3.0 = 2*R + 0.8  =>  R = 1.1 um
    R = 1.1
    
    # Width = Length_straight + 2*(Radius + w_wide/2)
    # 5.5 = L_straight + 3.0  =>  L_straight = 2.5 um
    L_straight = 2.5
    
    # Modulation Pattern
    # Pattern: Taper -> Gap -> Block -> Gap -> Block -> Gap -> Taper
    L_taper = 0.5
    L_gap = 0.2
    
    # We use a 5nm 'step' taper to handle the abrupt width change (0.2 -> 0.6)
    # This satisfies GDSFactory's port connectivity rules while looking instant visually.
    L_step = 0.005 
    
    # Calculate Block Length
    # L_straight = 2*L_taper + 3*L_gap + 2*L_block_visual
    # 2.5 = 1.0 + 0.6 + 2*L_block_visual  =>  0.9 = 2*L_block_visual  =>  L_block_visual = 0.45
    # Actual block straight length needs to subtract the step transitions
    L_block = 0.45 - 2*L_step

    # --- 2. Define Cross Sections ---
    # Explicitly set radius=R to allow the tight 1.1um bend without validation errors.
    xs_wide = gf.cross_section.cross_section(width=w_wide, layer=layer, radius=R)
    xs_narrow = gf.cross_section.cross_section(width=w_narrow, layer=layer, radius=R)
    xs_block = gf.cross_section.cross_section(width=w_block, layer=layer, radius=R)

    # --- 3. Construct Modulated Arm Sub-Component ---
    arm = gf.Component("modulated_arm")
    
    # -- Input Taper --
    t_in = arm << gf.components.taper(length=L_taper, width1=w_wide, width2=w_narrow, layer=layer)
    
    # -- Gap 1 --
    g1 = arm << gf.components.straight(length=L_gap, cross_section=xs_narrow)
    
    # -- Block 1 --
    su1 = arm << gf.components.taper(length=L_step, width1=w_narrow, width2=w_block, layer=layer)
    b1 = arm << gf.components.straight(length=L_block, cross_section=xs_block)
    sd1 = arm << gf.components.taper(length=L_step, width1=w_block, width2=w_narrow, layer=layer)
    
    # -- Gap 2 --
    g2 = arm << gf.components.straight(length=L_gap, cross_section=xs_narrow)
    
    # -- Block 2 --
    su2 = arm << gf.components.taper(length=L_step, width1=w_narrow, width2=w_block, layer=layer)
    b2 = arm << gf.components.straight(length=L_block, cross_section=xs_block)
    sd2 = arm << gf.components.taper(length=L_step, width1=w_block, width2=w_narrow, layer=layer)
    
    # -- Gap 3 --
    g3 = arm << gf.components.straight(length=L_gap, cross_section=xs_narrow)
    
    # -- Output Taper --
    t_out = arm << gf.components.taper(length=L_taper, width1=w_narrow, width2=w_wide, layer=layer)
    
    # -- Connect Primitives --
    g1.connect("o1", t_in.ports["o2"])
    
    su1.connect("o1", g1.ports["o2"])
    b1.connect("o1", su1.ports["o2"])
    sd1.connect("o1", b1.ports["o2"])
    
    g2.connect("o1", sd1.ports["o2"])
    
    su2.connect("o1", g2.ports["o2"])
    b2.connect("o1", su2.ports["o2"])
    sd2.connect("o1", b2.ports["o2"])
    
    g3.connect("o1", sd2.ports["o2"])
    
    t_out.connect("o1", g3.ports["o2"])
    
    # Expose Ports
    arm.add_port("o1", port=t_in.ports["o1"])
    arm.add_port("o2", port=t_out.ports["o2"])

    # --- 4. Main Assembly ---
    top_arm = c << arm
    bot_arm = c << arm
    
    # Define Bend
    # Use angle=-180 (Clockwise).
    # When attached to the Top Arm (going East), it turns South.
    # When attached to the Bottom Arm (going West), the connection logic rotates it 180.
    # A CW bend rotated 180 becomes a bend that turns North (closing the loop).
    bend = gf.components.bend_circular(radius=R, angle=-180, cross_section=xs_wide)
    
    br = c << bend
    bl = c << bend
    
    # Position Top Arm
    top_arm.move((0, 0))
    
    # Connect Right Bend (Top -> Down)
    br.connect("o1", top_arm.ports["o2"])
    
    # Connect Bottom Arm (Right Bend -> Left)
    bot_arm.connect("o2", br.ports["o2"])
    
    # Connect Left Bend (Bottom -> Up)
    bl.connect("o1", bot_arm.ports["o1"])

    return c

if __name__ == "__main__":
    device = racetrack_resonator_final()
    device.write_gds("racetrack_resonator.gds")
    device.show()