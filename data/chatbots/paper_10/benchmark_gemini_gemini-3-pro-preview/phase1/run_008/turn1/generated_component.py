import gdsfactory as gf

@gf.cell
def racetrack_resonator_fixed():
    """
    Recreation of the racetrack device with corrected geometry and validation settings.
    - Uses short 'step' tapers to resolve PortWidthMismatchError.
    - Sets explicit radius in CrossSection to resolve min_bend_radius ValueError.
    """
    c = gf.Component()

    # --- 1. Dimensions & Parameters ---
    # Target Footprint: 3.0 um (H) x 5.5 um (W)
    
    w_wide = 0.8        # Width of bends and taper ends
    w_narrow = 0.2      # Width of narrow straight sections
    w_block = 0.6       # Width of rectangular pads
    layer = (1, 0)
    
    # Calculate Radius (R) from Height
    # Height = 2*R + w_wide  =>  3.0 = 2*R + 0.8  =>  R = 1.1 um
    R = 1.1
    
    # Calculate Straight Length (L_straight) from Width
    # Width = L_straight + 2 * (R + w_wide/2)
    # 5.5 = L_straight + 2 * (1.1 + 0.4) = L_straight + 3.0  =>  L_straight = 2.5 um
    L_straight = 2.5
    
    # Length Distribution within Straight Arm
    # Structure: Taper -> Gap -> (Step->Block->Step) -> Gap -> (Step->Block->Step) -> Gap -> Taper
    L_taper = 0.5
    L_gap = 0.2
    L_step = 0.01  # Tiny transition length to fix Width Mismatch
    
    # Derive Block Length:
    # L_straight = 2*L_taper + 3*L_gap + 2*L_block + 4*L_step
    # 2.5 = 1.0 + 0.6 + 0.04 + 2*L_block
    # 2.5 = 1.64 + 2*L_block  =>  0.86 = 2*L_block  =>  L_block = 0.43 um
    L_block = 0.43

    # --- 2. Define Cross Sections ---
    # IMPORTANT: We explicitly pass `radius=R` to override the default 10.0um limit.
    xs_wide = gf.cross_section.cross_section(width=w_wide, layer=layer, radius=R)
    xs_narrow = gf.cross_section.cross_section(width=w_narrow, layer=layer, radius=R)
    xs_block = gf.cross_section.cross_section(width=w_block, layer=layer, radius=R)

    # --- 3. Construct Modulated Arm Sub-Component ---
    arm = gf.Component("modulated_arm")
    
    # -- Primitives --
    # Input Taper (Wide to Narrow)
    t_in = arm << gf.components.taper(length=L_taper, width1=w_wide, width2=w_narrow, layer=layer)
    
    # Gap 1
    g1 = arm << gf.components.straight(length=L_gap, cross_section=xs_narrow)
    
    # Block 1 (with step transitions)
    su1 = arm << gf.components.taper(length=L_step, width1=w_narrow, width2=w_block, layer=layer)
    b1 = arm << gf.components.straight(length=L_block, cross_section=xs_block)
    sd1 = arm << gf.components.taper(length=L_step, width1=w_block, width2=w_narrow, layer=layer)
    
    # Gap 2
    g2 = arm << gf.components.straight(length=L_gap, cross_section=xs_narrow)
    
    # Block 2 (with step transitions)
    su2 = arm << gf.components.taper(length=L_step, width1=w_narrow, width2=w_block, layer=layer)
    b2 = arm << gf.components.straight(length=L_block, cross_section=xs_block)
    sd2 = arm << gf.components.taper(length=L_step, width1=w_block, width2=w_narrow, layer=layer)
    
    # Gap 3
    g3 = arm << gf.components.straight(length=L_gap, cross_section=xs_narrow)
    
    # Output Taper (Narrow to Wide)
    t_out = arm << gf.components.taper(length=L_taper, width1=w_narrow, width2=w_wide, layer=layer)
    
    # -- Connections within Arm --
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
    
    # Expose Arm Ports
    arm.add_port("o1", port=t_in.ports["o1"])
    arm.add_port("o2", port=t_out.ports["o2"])

    # --- 4. Main Assembly ---
    top_arm = c << arm
    bot_arm = c << arm
    
    # Bends (using xs_wide with correctly defined radius)
    bend_r = c << gf.components.bend_circular(radius=R, angle=-180, cross_section=xs_wide)
    bend_l = c << gf.components.bend_circular(radius=R, angle=180, cross_section=xs_wide)
    
    # Positioning
    top_arm.move((0, 0))
    
    # Connect Loop
    bend_r.connect("o1", top_arm.ports["o2"])
    bot_arm.connect("o2", bend_r.ports["o2"])
    bend_l.connect("o1", bot_arm.ports["o1"])

    return c

if __name__ == "__main__":
    device = racetrack_resonator_fixed()
    device.write_gds("racetrack_resonator.gds")
    device.show()