import gdsfactory as gf
import numpy as np

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
    device_width = 3.0
    device_length = 5.5
    layer_device = (1, 0)

    # Ring Geometry
    ring_width = 0.6
    r_outer = device_width / 2.0  # 1.5
    r_inner = r_outer - ring_width # 0.9
    
    # Center radius for the waveguide path
    r_center = r_outer - ring_width / 2.0  # 1.2
    
    # Straight section length
    l_straight = device_length - device_width # 2.5
    
    # Arm Geometry
    arm_width = 0.5
    arm_y_offset = 0.65
    
    # Calculate intersection of arm with inner ring wall
    # The bend is centered at x = ±l_straight/2
    # We focus on the right side bend centered at x = l_straight/2
    # Equation of inner wall circle: (x - l_straight/2)^2 + y^2 = r_inner^2
    # We solve for x at y = arm_y_offset
    dx_intersect = np.sqrt(max(0, r_inner**2 - arm_y_offset**2))
    x_intersect = (l_straight / 2.0) + dx_intersect
    
    # Arm Dimensions
    beam_length = 1.0 # Length of the central uniform section
    
    # Taper length: from end of beam to intersection point + slight overlap
    taper_overshoot = 0.1
    # Beam extends from -0.5 to 0.5. Taper starts at 0.5.
    # It must reach x_intersect.
    taper_length = (x_intersect - (beam_length / 2.0)) + taper_overshoot
    
    taper_width_narrow = arm_width
    taper_width_wide = 0.8 # Flare out to merge cleanly
    
    # Hole Parameters
    hole_w = 0.4
    hole_h = 0.25
    hole_gap = 0.25

    # Define Cross Sections
    # FIX: Set radius_min=0.5 to allow the tight bend radius of 1.2
    # Default radius_min is often 10.0, which causes ValueError
    xs_ring = gf.cross_section.cross_section(
        width=ring_width, 
        layer=layer_device, 
        radius=r_center,
        radius_min=0.5 
    )
    xs_arm = gf.cross_section.cross_section(width=arm_width, layer=layer_device)

    # =========================================================================
    # 2. Build the Ring
    # =========================================================================
    ring_parts = gf.Component()
    
    # Create straights
    s_top = ring_parts << gf.components.straight(length=l_straight, cross_section=xs_ring)
    s_bot = ring_parts << gf.components.straight(length=l_straight, cross_section=xs_ring)
    
    # Move straights to correct positions
    # s_top: y=+1.2, centered x
    s_top.move( (-l_straight/2, r_center) )
    # s_bot: y=-1.2, centered x
    s_bot.move( (-l_straight/2, -r_center) )
    
    # Create bends
    # Note: radius is explicit here, but cross_section is also passed for width info
    b_right = ring_parts << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs_ring)
    b_left = ring_parts << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs_ring)
    
    # Connect bends
    # Right bend connects to bottom straight's right port (o2)
    b_right.connect("o1", s_bot.ports["o2"])
    # Left bend connects to top straight's left port (o1)
    b_left.connect("o1", s_top.ports["o1"])

    # =========================================================================
    # 3. Build the Arm (Solid geometry minus holes)
    # =========================================================================
    # Step 3a: Create the solid arm shape (Beam + Tapers)
    solid_arm = gf.Component()
    
    # Central Beam
    beam = solid_arm << gf.components.straight(length=beam_length, cross_section=xs_arm)
    beam.center = (0, 0)
    
    # Right Taper
    t_right = solid_arm << gf.components.taper(
        length=taper_length,
        width1=taper_width_narrow,
        width2=taper_width_wide,
        layer=layer_device
    )
    t_right.connect("o1", beam.ports["o2"])
    
    # Left Taper
    t_left = solid_arm << gf.components.taper(
        length=taper_length,
        width1=taper_width_narrow,
        width2=taper_width_wide,
        layer=layer_device
    )
    # Connect taper input (narrow) to beam input (narrow/left)
    # This automatically rotates t_left to point West
    t_left.connect("o1", beam.ports["o1"])
    
    # Step 3b: Create Holes
    holes_layer = gf.Component()
    h_rect = gf.components.rectangle(size=(hole_w, hole_h), layer=layer_device, centered=True)
    
    # Left hole
    h1 = holes_layer << h_rect
    h1.movex( - (hole_w + hole_gap)/2.0 )
    
    # Right hole
    h2 = holes_layer << h_rect
    h2.movex( (hole_w + hole_gap)/2.0 )
    
    # Step 3c: Subtract Holes from Solid Arm
    # We use boolean "not" to cut holes
    arm_final = gf.boolean(solid_arm, holes_layer, operation="not", layer=layer_device)
    
    # =========================================================================
    # 4. Final Assembly (Boolean Union)
    # =========================================================================
    # We arrange the arms relative to the ring center
    arms_layout = gf.Component()
    
    # Top Arm
    a_top = arms_layout << arm_final
    a_top.movey(arm_y_offset)
    
    # Bottom Arm
    a_bot = arms_layout << arm_final
    a_bot.movey(-arm_y_offset)
    
    # Merge Ring and Arms
    # FIX: Use explicit components for boolean to avoid 'list' attribute error
    merged_device = gf.boolean(ring_parts, arms_layout, operation="or", layer=layer_device)
    
    c << merged_device

    return c

if __name__ == "__main__":
    device = device_racetrack_mems()
    device.show()
    device.write_gds("racetrack_mems.gds")