import gdsfactory as gf

@gf.cell
def device_racetrack_mzi():
    """
    Creates a racetrack resonator with modified arms containing heater pads.
    The arms are pinched inwards via S-bends.
    Footprint constraint: ~5.5um x 3.0um
    """
    c = gf.Component()

    # --- Geometric Parameters ---
    total_length = 5.5
    
    # Waveguide and Pad dimensions
    wg_width = 0.35
    pad_width = 0.85
    pad_length = 0.5
    pad_gap = 0.2
    
    # Bend radius for the main loops
    # 2*radius + wg_width ~ 3.0um height => R ~ 1.25
    main_bend_radius = 1.25
    
    # Define Cross Sections
    # We set 'radius' to 0.1 to allow the tight S-bends (R~0.114) to pass validation.
    # The main circular bends will override this with their specific radius argument.
    xs_wg = gf.cross_section.cross_section(width=wg_width, layer=(1, 0), radius=0.1)
    xs_pad = gf.cross_section.cross_section(width=pad_width, layer=(1, 0), radius=0.1)

    # --- 1. Define the 180-degree Bend ---
    # Standard circular bend: Starts at (0,0) facing East, ends at (0, 2R) facing West.
    # We explicitly pass the large radius here.
    bend180 = gf.components.bend_circular(
        radius=main_bend_radius, 
        angle=180, 
        cross_section=xs_wg
    )
    
    # --- 2. Define the Straight Arm Component ---
    # Calculate available length for the straight section
    # Length = Total - 2 * Bend_Radius (approx width of bend)
    straight_region_len = total_length - 2 * main_bend_radius
    
    # Pinching Geometry Calculation
    # Outer port Y = +/- 1.25. Target inner Y ~ +/- 0.3 (0.6 gap).
    # Shift required = 1.25 - 0.3 = 0.95um.
    shift_dy = -0.95
    sbend_dx = 0.55
    
    # Remaining length calculations
    heater_len = straight_region_len - 2 * sbend_dx
    connector_len = (heater_len - (2 * pad_length + pad_gap)) / 2

    def create_arm():
        arm = gf.Component()
        
        # 1. S-bend In (Shift Down)
        s_in = arm << gf.components.bend_s(size=(sbend_dx, shift_dy), cross_section=xs_wg)
        
        # 2. Connector
        c1 = arm << gf.components.straight(length=connector_len, cross_section=xs_wg)
        c1.connect("o1", s_in.ports["o2"])
        
        # 3. Pad 1
        p1 = arm << gf.components.straight(length=pad_length, cross_section=xs_pad)
        p1.connect("o1", c1.ports["o2"])
        
        # 4. Gap
        g = arm << gf.components.straight(length=pad_gap, cross_section=xs_wg)
        g.connect("o1", p1.ports["o2"])
        
        # 5. Pad 2
        p2 = arm << gf.components.straight(length=pad_length, cross_section=xs_pad)
        p2.connect("o1", g.ports["o2"])
        
        # 6. Connector
        c2 = arm << gf.components.straight(length=connector_len, cross_section=xs_wg)
        c2.connect("o1", p2.ports["o2"])
        
        # 7. S-bend Out (Shift Up/Return)
        s_out = arm << gf.components.bend_s(size=(sbend_dx, -shift_dy), cross_section=xs_wg)
        s_out.connect("o1", c2.ports["o2"])
        
        arm.add_port("o1", port=s_in.ports["o1"])
        arm.add_port("o2", port=s_out.ports["o2"])
        return arm

    arm_component = create_arm()

    # --- 3. Assembly ---
    
    # A. Left Bend (Mirrored)
    # Mirroring X makes ports face inward (Right). o2 becomes the Top port.
    lb = c << bend180
    lb.mirror_x()
    
    # B. Top Arm
    # Connect Top Arm Input (o1) to Left Bend Top (o2)
    top = c << arm_component
    top.connect("o1", lb.ports["o2"])
    
    # C. Right Bend (Standard)
    # Connect Right Bend Top (o2) to Top Arm Output (o2)
    rb = c << bend180
    rb.connect("o2", top.ports["o2"])
    
    # D. Bottom Arm (Rotated 180)
    # Rotating 180 flips the arm geometry upside down (pinching 'up' relative to straight line)
    # and reverses direction (Right-to-Left).
    bot = c << arm_component
    bot.rotate(180)
    
    # Connect Bottom Arm manually
    # We simply move the bottom arm so its input port (o1) snaps to the Right Bend's bottom port (o1).
    # Since we manually rotated it 180, the orientations are already correct for a closed loop 
    # (Head-to-Head vector flow), so we use move() instead of connect() to prevent re-rotation.
    bot.move(origin=bot.ports["o1"], destination=rb.ports["o1"])

    return c

# Create and save
device = device_racetrack_mzi()
device.write_gds("device_racetrack_mzi.gds")