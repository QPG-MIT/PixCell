import gdsfactory as gf

@gf.cell
def device_racetrack_mems():
    """
    Creates a racetrack resonator with internal suspended MEMS-like structures.
    Target footprint: 5.5 um x 3.0 um.
    """
    c = gf.Component()

    # =========================================================================
    # 1. Define Parameters
    # =========================================================================
    # Dimensions
    total_width = 3.0
    total_length = 5.5
    layer_device = (1, 0)

    # Geometry Parameters
    ring_width = 0.6        # Thickness of the outer racetrack ring
    arm_width = 0.5         # Width of the internal horizontal arms
    arm_offset_y = 0.65     # Vertical position of the arms from center
    
    # Racetrack calculations
    r_outer = total_width / 2.0
    # Center radius for the waveguide path (1.5 - 0.3 = 1.2)
    r_center = r_outer - ring_width / 2.0
    # Length of the straight sections
    l_straight = total_length - total_width  # 5.5 - 3.0 = 2.5
    
    # Arm detail parameters
    taper_length = 0.6
    taper_width_wide = 1.2
    
    # Hole parameters
    hole_width = 0.7
    hole_height = 0.25
    hole_gap = 0.25

    # =========================================================================
    # 2. Define Cross Sections
    # =========================================================================
    # We explicitly set 'radius' to r_center (1.2) to prevent the ValueError
    # regarding min_bend_radius constraints.
    xs_ring = gf.cross_section.cross_section(
        width=ring_width, 
        layer=layer_device, 
        radius=r_center
    )
    
    xs_arm = gf.cross_section.cross_section(
        width=arm_width, 
        layer=layer_device
    )

    # =========================================================================
    # 3. Build the Outer Racetrack Ring
    # =========================================================================
    ring_parts = gf.Component()
    
    # Straights
    s_top = ring_parts << gf.components.straight(length=l_straight, cross_section=xs_ring)
    s_bot = ring_parts << gf.components.straight(length=l_straight, cross_section=xs_ring)
    
    # Position straights: Center is (0,0)
    # s_top centered at y = +r_center
    s_top.move(( -l_straight/2, r_center ))
    # s_bot centered at y = -r_center
    s_bot.move(( -l_straight/2, -r_center ))
    
    # Bends
    # Right Bend (180 deg)
    b_right = ring_parts << gf.components.bend_circular(
        radius=r_center, 
        angle=180, 
        cross_section=xs_ring
    )
    # Connect start of bend (o1) to end of top straight (o2)
    b_right.connect("o1", s_top.ports["o2"])
    
    # Left Bend (180 deg)
    b_left = ring_parts << gf.components.bend_circular(
        radius=r_center, 
        angle=180, 
        cross_section=xs_ring
    )
    # Connect start of bend (o1) to start of bottom straight (o1) [Faces West]
    # This orients the bend to loop correctly on the left side
    b_left.connect("o1", s_bot.ports["o1"])

    # =========================================================================
    # 4. Build the Inner Arm Structure (with holes)
    # =========================================================================
    arm_proto = gf.Component()
    
    # Central Beam
    beam = arm_proto << gf.components.straight(length=l_straight, cross_section=xs_arm)
    beam.movex(-l_straight/2)
    
    # Tapers (Flares connecting to the ring)
    t_right = arm_proto << gf.components.taper(
        length=taper_length, 
        width1=arm_width, 
        width2=taper_width_wide, 
        cross_section=xs_arm
    )
    t_right.connect("o1", beam.ports["o2"])
    
    t_left = arm_proto << gf.components.taper(
        length=taper_length, 
        width1=arm_width, 
        width2=taper_width_wide, 
        cross_section=xs_arm
    )
    t_left.connect("o1", beam.ports["o1"])
    
    # Holes (Rectangular Cutouts)
    holes_proto = gf.Component()
    rect = gf.components.rectangle(size=(hole_width, hole_height), layer=layer_device, centered=True)
    
    h1 = holes_proto << rect
    h1.movex(-(hole_width + hole_gap)/2)
    
    h2 = holes_proto << rect
    h2.movex((hole_width + hole_gap)/2)
    
    # Subtract holes from arm
    arm_with_holes = gf.boolean(arm_proto, holes_proto, operation="not", layer=layer_device)

    # =========================================================================
    # 5. Final Assembly
    # =========================================================================
    arms_layout = gf.Component()
    
    # Place top and bottom arms
    ref_top = arms_layout << arm_with_holes
    ref_top.movey(arm_offset_y)
    
    ref_bot = arms_layout << arm_with_holes
    ref_bot.movey(-arm_offset_y)
    
    # Merge Ring and Arms (Union)
    final_shape = gf.boolean(ring_parts, arms_layout, operation="or", layer=layer_device)
    
    c << final_shape
    return c

if __name__ == "__main__":
    device = device_racetrack_mems()
    device.show()
    device.write_gds("racetrack_mems.gds")