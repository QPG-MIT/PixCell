import gdsfactory as gf

@gf.cell
def racetrack_resonator_with_couplers():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(
        width=0.5, 
        layer=(1, 0),
        radius=5.0,
        radius_min=1.0
    )
    
    # Create the outer racetrack shape using boolean operations
    # We'll create a rectangle with two half-circles on the ends
    
    # Parameters for the racetrack
    straight_length = 2.0
    bend_radius = 0.75
    track_width = 1.5  # height of the racetrack
    
    # Create the main rectangle (straight section)
    main_rect = c << gf.components.rectangle(
        size=(straight_length, track_width), 
        layer=(1, 0)
    )
    main_rect.move((-straight_length/2, -track_width/2))
    
    # Create two full circles for the ends
    left_circle = c << gf.components.circle(
        radius=bend_radius, 
        layer=(1, 0)
    )
    left_circle.move((-straight_length/2, 0))
    
    right_circle = c << gf.components.circle(
        radius=bend_radius, 
        layer=(1, 0)
    )
    right_circle.move((straight_length/2, 0))
    
    # Create a rectangle that will be used to cut the circles in half
    # This rectangle will be the same height as the track and extend beyond the circles
    cut_rect_height = track_width + 0.1  # slightly taller to ensure clean cut
    cut_rect_width = 2 * bend_radius + 0.1
    
    # Create the cut rectangle for the left side
    left_cut_rect = c << gf.components.rectangle(
        size=(cut_rect_width, cut_rect_height), 
        layer=(1, 0)
    )
    left_cut_rect.move((-straight_length/2 - bend_radius, -cut_rect_height/2))
    
    # Create the cut rectangle for the right side
    right_cut_rect = c << gf.components.rectangle(
        size=(cut_rect_width, cut_rect_height), 
        layer=(1, 0)
    )
    right_cut_rect.move((straight_length/2 - bend_radius, -cut_rect_height/2))
    
    # Use boolean operations to create half-circles
    # First, create the left half-circle by intersecting the circle with the cut rectangle
    left_half_circle = c << gf.boolean(
        left_circle, 
        left_cut_rect, 
        operation="and", 
        layer=(1, 0)
    )
    
    # Create the right half-circle by intersecting the circle with the cut rectangle
    right_half_circle = c << gf.boolean(
        right_circle, 
        right_cut_rect, 
        operation="and", 
        layer=(1, 0)
    )
    
    # Now combine all elements to form the racetrack
    racetrack = c << gf.boolean(
        main_rect, 
        left_half_circle, 
        operation="or", 
        layer=(1, 0)
    )
    racetrack = c << gf.boolean(
        racetrack, 
        right_half_circle, 
        operation="or", 
        layer=(1, 0)
    )
    
    # Create the two coupling waveguides in the center
    coupling_length = 1.0
    gap_between_waveguides = 0.5
    
    # Create straight waveguides for coupling
    top_coupler = c << gf.components.straight(length=coupling_length, cross_section=xs)
    bottom_coupler = c << gf.components.straight(length=coupling_length, cross_section=xs)
    
    # Position the coupling waveguides
    top_coupler.move((0.0, gap_between_waveguides/2))
    bottom_coupler.move((0.0, -gap_between_waveguides/2))
    
    # Create the rectangular coupling regions (these are wider sections)
    coupling_width = 0.8
    coupling_height = 0.3
    
    # Create rectangles for the coupling regions
    top_rect1 = c << gf.components.rectangle(size=(coupling_width, coupling_height), layer=(1, 0))
    top_rect2 = c << gf.components.rectangle(size=(coupling_width, coupling_height), layer=(1, 0))
    bottom_rect1 = c << gf.components.rectangle(size=(coupling_width, coupling_height), layer=(1, 0))
    bottom_rect2 = c << gf.components.rectangle(size=(coupling_width, coupling_height), layer=(1, 0))
    
    # Position the rectangles
    top_rect1.move((-coupling_width/2 - 0.2, gap_between_waveguides/2))
    top_rect2.move((coupling_width/2 + 0.2, gap_between_waveguides/2))
    bottom_rect1.move((-coupling_width/2 - 0.2, -gap_between_waveguides/2))
    bottom_rect2.move((coupling_width/2 + 0.2, -gap_between_waveguides/2))
    
    return c

# Create the device
device = racetrack_resonator_with_couplers()
device.write_gds("racetrack_resonator_with_couplers.gds")