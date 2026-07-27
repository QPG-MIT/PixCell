import gdsfactory as gf

@gf.cell
def racetrack_modulator_fixed():
    c = gf.Component()

    # =======================================================================
    # 1. Define Dimensions & Parameters
    # =======================================================================
    # Derived from footprint 5.5um x 3.0um
    height = 3.0
    width = 5.5
    
    ring_width = 0.5
    # Outer radius is half the height (1.5). 
    # Center radius is Outer - half_width.
    r_center = (height / 2.0) - (ring_width / 2.0)  # 1.25um
    
    # Length of the straight sections
    l_straight = width - height  # 2.5um
    
    # Inner Structure parameters
    arm_width = 0.15
    arm_gap = 0.5
    y_arm_offset = (arm_gap + arm_width) / 2.0
    pad_size = (0.7, 0.45)
    
    # Layer definition (GDS layer 1, datatype 0)
    layer_wg = (1, 0)

    # =======================================================================
    # 2. Define Custom Cross-Sections (THE FIX)
    # =======================================================================
    # We explicitly set 'radius' to r_center (1.25) to prevent the ValueError.
    # This tells GDSFactory that this tight bend is intentional.
    xs_ring = gf.cross_section.cross_section(
        width=ring_width, 
        layer=layer_wg, 
        radius=r_center 
    )
    
    xs_inner = gf.cross_section.cross_section(
        width=arm_width, 
        layer=layer_wg
    )

    # =======================================================================
    # 3. Build Outer Racetrack Ring
    # =======================================================================
    # Create the primitives
    straight = gf.components.straight(length=l_straight, cross_section=xs_ring)
    bend = gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs_ring)
    
    # Add references
    s_top = c << straight
    s_bot = c << straight
    b_left = c << bend
    b_right = c << bend
    
    # Position the top and bottom straights
    s_top.movex(-l_straight/2).movey(r_center)
    s_bot.movex(-l_straight/2).movey(-r_center)
    
    # Connect the bends to form the loop
    # Connect the top port of the left bend to the left port of the top straight
    b_left.connect("o2", s_top.ports["o1"])
    # Connect the bottom port of the right bend to the right port of the bottom straight
    b_right.connect("o1", s_bot.ports["o2"])

    # =======================================================================
    # 4. Build Inner Arms Assembly
    # =======================================================================
    # Calculate available space
    conn_len = 0.35 # Length of the tapered connection block
    arm_len = l_straight - (2 * conn_len)
    
    # Helper function to create one arm with pads
    def create_arm_segment():
        cmp = gf.Component()
        # Waveguide
        wg = cmp << gf.components.straight(length=arm_len, cross_section=xs_inner)
        wg.movex(-arm_len/2) # Center at 0
        
        # Pads
        p1 = cmp << gf.components.rectangle(size=pad_size, layer=layer_wg, centered=True)
        p1.movex(-arm_len/4)
        p2 = cmp << gf.components.rectangle(size=pad_size, layer=layer_wg, centered=True)
        p2.movex(arm_len/4)
        
        # Expose ports
        cmp.add_port("o1", port=wg.ports["o1"])
        cmp.add_port("o2", port=wg.ports["o2"])
        return cmp

    # Create and place the two arms
    arm_comp = create_arm_segment()
    
    top_arm = c << arm_comp
    top_arm.movey(y_arm_offset)
    
    bot_arm = c << arm_comp
    bot_arm.movey(-y_arm_offset)

    # =======================================================================
    # 5. Build Connections (Tapers)
    # =======================================================================
    # Use a Taper component to bridge the gap between the ring edge and the arms.
    # This creates the solid trapezoidal blocks seen in the image.
    
    connector_width = (2 * y_arm_offset) + arm_width
    
    connector = gf.components.taper(
        length=conn_len,
        width1=connector_width * 0.7, # Slightly narrower at the ring interface
        width2=connector_width,       # Full width at the arms interface
        cross_section=xs_inner
    )
    
    # Left Connector
    conn_l = c << connector
    # Position: right edge (o2) at the start of the arms
    conn_l.connect("o2", top_arm.ports["o1"], allow_layer_mismatch=True)
    # Adjust Y to be centered (since we connected to the top arm)
    conn_l.movey(-y_arm_offset)
    
    # Right Connector
    conn_r = c << connector
    conn_r.mirror() # Flip horizontally
    conn_r.connect("o2", top_arm.ports["o2"], allow_layer_mismatch=True)
    conn_r.movey(-y_arm_offset)

    return c

# Generate and save
device = racetrack_modulator_fixed()
device.write_gds("racetrack_modulator.gds")
device.show()