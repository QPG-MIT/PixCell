import gdsfactory as gf

@gf.cell
def tapered_fork_geometry():
    c = gf.Component()

    # --- 1. Define Cross-Sections ---
    # Center taper: Thick to Thin
    xs_c_start = gf.cross_section.cross_section(width=0.6, layer=(1, 0))
    xs_c_end = gf.cross_section.cross_section(width=0.1, layer=(1, 0))
    
    # Side taper: Wide -> Thin (waist) -> Wide
    xs_s_start = gf.cross_section.cross_section(width=0.3, layer=(1, 0))
    xs_s_mid = gf.cross_section.cross_section(width=0.1, layer=(1, 0))
    xs_s_end = gf.cross_section.cross_section(width=0.3, layer=(1, 0))

    # --- 2. Construct Center Arm ---
    # Using path extrude_transition for better control
    p_center = gf.path.straight(length=40)
    t_center = gf.path.transition(xs_c_start, xs_c_end)
    center_wg = c << gf.path.extrude_transition(p_center, t_center)

    # --- 3. Construct Side Arm (Sub-component) ---
    @gf.cell
    def side_arm():
        c_arm = gf.Component()
        
        # Segment 1: Wide to Narrow (Straight)
        p1 = gf.path.straight(length=15)
        # Segment 2: Narrow to Wide (Curved)
        p2 = gf.path.euler(radius=30, angle=10) + gf.path.straight(length=25)
        
        # Extrude segments
        arm_in = c_arm << gf.path.extrude_transition(p1, gf.path.transition(xs_s_start, xs_s_mid))
        arm_out = c_arm << gf.path.extrude_transition(p2, gf.path.transition(xs_s_mid, xs_s_end))
        
        # Connect the two segments
        # FIX: Removed 'destination=' keyword argument
        arm_out.connect("o1", arm_in.ports["o2"])
        
        # Expose ports
        c_arm.add_port("o1", port=arm_in.ports["o1"])
        c_arm.add_port("o2", port=arm_out.ports["o2"])
        return c_arm

    # --- 4. Assemble ---
    side = side_arm()
    
    # Add top arm
    top = c << side
    top.movey(0.7) 
    
    # Add bottom arm (mirrored)
    bottom = c << side
    bottom.mirror_y() 
    bottom.movey(-0.7)

    return c

# Create and save
device = tapered_fork_geometry()
device.write_gds("fork_device.gds")