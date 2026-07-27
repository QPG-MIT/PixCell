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
    # Device envelope
    width = 3.0
    length = 5.5
    layer_device = (1, 0)

    # Geometry Parameters
    ring_width = 0.6
    arm_width = 0.5
    arm_offset_y = 0.65
    
    # Racetrack calculations
    # Outer radius is half the width
    r_outer = width / 2.0  # 1.5
    # Radius for the center of the waveguide path
    r_center = r_outer - ring_width / 2.0  # 1.2
    # Length of the straight sections
    l_straight = length - width  # 2.5
    
    # Arm detail parameters (Tuned to match visual proportions and intersection)
    # The central beam must be long enough to hold the holes.
    # The tapers must be long enough to penetrate the inner wall of the ring.
    # Inner wall at y=0.65 is approx at x=1.87. We aim for x=2.0 overlap.
    beam_length = 1.8      # Central straight section
    taper_length = 1.1     # Length of the flared connection
    taper_width_tip = 1.0  # Width at the ring connection (flared)
    
    # Hole parameters
    hole_width = 0.7
    hole_height = 0.25
    hole_gap = 0.25

    # Define Cross Sections
    # We explicitly set 'radius' to r_center (1.2) to prevent min_bend_radius errors
    xs_ring = gf.cross_section.cross_section(width=ring_width, layer=layer_device, radius=r_center)
    xs_arm = gf.cross_section.cross_section(width=arm_width, layer=layer_device)

    # =========================================================================
    # 2. Build the Outer Racetrack Ring
    # =========================================================================
    ring_parts = gf.Component()
    
    # Straight sections
    s_top = ring_parts << gf.components.straight(length=l_straight, cross_section=xs_ring)
    s_bot = ring_parts << gf.components.straight(length=l_straight, cross_section=xs_ring)
    
    # Center straights vertically and horizontally
    s_top.move(( -l_straight/2, r_center ))
    s_bot.move(( -l_straight/2, -r_center ))
    
    # Bends
    # Right Bend (connects East ends)
    b_right = ring_parts << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs_ring)
    b_right.connect("o1", s_top.ports["o2"])
    
    # Left Bend (connects West ends)
    # We connect the start of the bend to the bottom straight's left port.
    b_left = ring_parts << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs_ring)
    b_left.connect("o1", s_bot.ports["o1"])

    # =========================================================================
    # 3. Build the Inner Arms (with Tapers and Holes)
    # =========================================================================
    # Create a single arm prototype
    arm_proto = gf.Component()
    
    # Central Beam
    beam = arm_proto << gf.components.straight(length=beam_length, cross_section=xs_arm)
    beam.center = (0, 0)  # Center the beam at local origin
    
    # Tapers (Connect beam to ring)
    # Left Taper: Flares out from arm_width to taper_width_tip
    t_left = arm_proto << gf.components.taper(
        length=taper_length, 
        width1=arm_width, 
        width2=taper_width_tip, 
        cross_section=xs_arm
    )
    t_left.connect("o1", beam.ports["o1"])
    
    # Right Taper
    t_right = arm_proto << gf.components.taper(
        length=taper_length, 
        width1=arm_width, 
        width2=taper_width_tip, 
        cross_section=xs_arm
    )
    t_right.connect("o1", beam.ports["o2"])
    
    # Holes (Rectangles)
    holes_proto = gf.Component()
    hole_rect = gf.components.rectangle(size=(hole_width, hole_height), layer=layer_device, centered=True)
    
    # Left hole
    h1 = holes_proto << hole_rect
    h1.movex(-(hole_width + hole_gap)/2)
    
    # Right hole
    h2 = holes_proto << hole_rect
    h2.movex((hole_width + hole_gap)/2)
    
    # Subtract holes from the arm shape
    arm_final = gf.boolean(arm_proto, holes_proto, operation="not", layer=layer_device)

    # =========================================================================
    # 4. Final Assembly
    # =========================================================================
    arms_layout = gf.Component()
    
    # Instantiate Top Arm
    arm_top = arms_layout << arm_final
    arm_top.movey(arm_offset_y)
    
    # Instantiate Bottom Arm
    arm_bot = arms_layout << arm_final
    arm_bot.movey(-arm_offset_y)
    
    # Merge Ring and Arms into one solid layer
    final_shape = gf.boolean(ring_parts, arms_layout, operation="or", layer=layer_device)
    
    c << final_shape
    return c

if __name__ == "__main__":
    device = device_racetrack_mems()
    device.show()
    device.write_gds("racetrack_mems.gds")