import gdsfactory as gf

@gf.cell
def generated_device():
    """
    Recreation of the dense waveguide coupler/array using parametric primitives
    and boolean subtraction to achieve the straight outer edge profile.
    
    Dimensions: 120um x 4um
    """
    c = gf.Component()

    # 1. Define Geometric Parameters
    length_total = 120.0
    width_total = 4.0
    
    # Segment lengths based on visual proportions
    length_bend = 20.0
    length_straight = 80.0 # Center coupling region
    
    # Gap configuration (the white lines in the image)
    # Visual analysis shows 4 distinct gaps separating 5 waveguide rails
    gap_width = 0.15
    gap_layer = (2, 0) # Temporary layer for boolean operations
    
    # Y-positions for the 4 gaps at the ends (Input/Output) and Center
    # Spacing is wider at ends, tighter in center.
    # Symmetry is +/- Y.
    y_gaps_input = [1.4, 0.5, -0.5, -1.4]
    y_gaps_center = [0.5, 0.18, -0.18, -0.5]

    # 2. Construct the "Negative" Mask (The Gaps)
    # We create a component that contains the geometry of the empty space
    gaps_component = gf.Component()
    xs_gap = gf.cross_section.cross_section(width=gap_width, layer=gap_layer)

    for y_in, y_cen in zip(y_gaps_input, y_gaps_center):
        # Calculate vertical displacement for the S-bend
        dy = y_cen - y_in
        
        # A. Left Fan-In S-Bend
        bend_in = gaps_component << gf.components.bend_s(
            size=(length_bend, dy), 
            cross_section=xs_gap
        )
        # Position the start of the bend at the left edge of the device
        bend_in.move((-length_total/2, y_in))
        
        # B. Center Straight Section
        straight = gaps_component << gf.components.straight(
            length=length_straight, 
            cross_section=xs_gap
        )
        straight.connect("o1", bend_in.ports["o2"])
        
        # C. Right Fan-Out S-Bend
        # Note: dy is inverted to return to the original Y position
        bend_out = gaps_component << gf.components.bend_s(
            size=(length_bend, -dy), 
            cross_section=xs_gap
        )
        bend_out.connect("o1", straight.ports["o2"])

    # 3. Construct the Main Body
    # A solid rectangle representing the full footprint
    main_body = gf.components.rectangle(
        size=(length_total, width_total), 
        layer=(1, 0), 
        centered=True
    )

    # 4. Boolean Operation
    # Subtract the gaps from the main body to create the waveguides
    # This guarantees the flat outer edges seen in the image (Top/Bottom)
    final_geometry = gf.boolean(
        A=main_body,
        B=gaps_component,
        operation="not",
        layer=(1, 0)
    )

    # Add the result to the main component
    c.add_ref(final_geometry)
    
    # Add ports (optional, placed at the main waveguide inputs)
    # We define ports based on the calculated gap positions to align with the core material
    c.add_port("o1", center=(-length_total/2, 0), width=width_total, orientation=180, layer=(1,0))
    c.add_port("o2", center=(length_total/2, 0), width=width_total, orientation=0, layer=(1,0))

    return c

# Create and save the device
device = generated_device()
device.write_gds("dense_coupler_array.gds")
device.show()