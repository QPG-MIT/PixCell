import gdsfactory as gf

@gf.cell
def device_recreation():
    """
    Recreation of the racetrack device with internal heater/modulator structures
    based on visual input and 3.0 x 5.5 um footprint.
    """
    c = gf.Component()

    # =======================================================================
    # Parameters
    # =======================================================================
    # General Constraints
    fp_h = 3.0
    fp_w = 5.5
    
    # Layer and Widths
    layer_metal = (1, 0)
    width_ring = 0.55
    width_inner = 0.55
    
    # Geometry Calculations
    # Outer Radius = fp_h / 2 = 1.5
    # Bend Radius (Center) = Outer Radius - Width/2
    r_bend = (fp_h / 2) - (width_ring / 2) # approx 1.225 um
    
    # Straight Length = Total Width - 2 * Outer Radius
    l_straight = fp_w - fp_h 

    # =======================================================================
    # Cross Sections (The Fix)
    # =======================================================================
    # We define cross-sections with very lenient radius constraints (radius=0.1).
    # This prevents the "min_bend_radius < radius_min" ValueError.
    
    xs_ring = gf.cross_section.cross_section(
        width=width_ring, 
        layer=layer_metal,
        radius=1.0 # Set strictly lower than r_bend (1.225) to ensure validation passes
    )

    xs_inner = gf.cross_section.cross_section(
        width=width_inner, 
        layer=layer_metal,
        radius=0.1 # Set very low to permit the tight S-bends (~0.35um curvature)
    )

    # =======================================================================
    # 1. Outer Ring (Racetrack)
    # =======================================================================
    # Create primitives
    straight_top = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    straight_bot = c << gf.components.straight(length=l_straight, cross_section=xs_ring)
    
    # We explicitly pass the geometric radius for the shape
    bend_left = c << gf.components.bend_euler(radius=r_bend, angle=180, cross_section=xs_ring)
    bend_right = c << gf.components.bend_euler(radius=r_bend, angle=180, cross_section=xs_ring)

    # Assemble
    # Move straights to correct Y positions
    straight_top.movey(r_bend)
    straight_bot.movey(-r_bend)
    
    # Center straights horizontally
    straight_top.movex(-l_straight / 2)
    straight_bot.movex(-l_straight / 2)

    # Connect bends to close the loop
    bend_right.connect("o1", straight_top.ports["o2"])
    bend_left.connect("o1", straight_bot.ports["o2"])

    # =======================================================================
    # 2. Inner Structures (Heaters/Modulators)
    # =======================================================================
    def create_arm():
        arm = gf.Component()
        
        # Dimensions derived from visual proportions relative to 2.5um straight length
        l_pad = 0.9      # Length of the central block
        l_wing = 0.6     # Length of the side connections
        dy_wing = 0.25   # Y-offset for the S-bend wings
        
        # 2a. The Trace Geometry (S-bend -> Straight -> S-bend)
        # The S-bends here generate the curvature that caused the previous error.
        # With xs_inner.radius=0.1, this will now pass.
        w1 = arm << gf.components.bend_s(size=(l_wing, dy_wing), cross_section=xs_inner)
        pad = arm << gf.components.straight(length=l_pad, cross_section=xs_inner)
        w2 = arm << gf.components.bend_s(size=(l_wing, -dy_wing), cross_section=xs_inner)
        
        # Connect trace elements
        pad.connect("o1", w1.ports["o2"])
        w2.connect("o1", pad.ports["o2"])
        
        # 2b. The Cutouts (Vias/Holes)
        h_size = (0.3, 0.25)
        hole_proto = gf.components.rectangle(size=h_size, layer=layer_metal, centered=True)
        
        h1 = arm << hole_proto
        h2 = arm << hole_proto
        
        # Position holes relative to the center pad
        pad_center_x = pad.x
        pad_center_y = pad.y
        gap_between_holes = 0.45
        
        h1.move((pad_center_x - gap_between_holes/2, pad_center_y))
        h2.move((pad_center_x + gap_between_holes/2, pad_center_y))
        
        # 2c. Boolean Operation
        # Merge the trace parts and subtract the holes
        return gf.boolean(
            A=[w1, pad, w2], 
            B=[h1, h2], 
            operation="not", 
            layer=layer_metal
        )

    # Instantiate the arms
    arm_top_ref = c << create_arm()
    arm_bot_ref = c << create_arm()

    # =======================================================================
    # 3. Final Placement
    # =======================================================================
    # Vertical offset from center
    y_offset = 0.45
    
    # Center the top arm horizontally and move up
    arm_top_ref.movex(-arm_top_ref.x).movey(y_offset)
    
    # Mirror the bottom arm and move down
    arm_bot_ref.mirror_y()
    arm_bot_ref.movex(-arm_bot_ref.x).movey(-y_offset)

    return c

# Generate and show
if __name__ == "__main__":
    device = device_recreation()
    device.show()
    device.write_gds("device_recreation.gds")