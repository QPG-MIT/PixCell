import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define layer
    layer = (1, 0)
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=layer)
    
    # Define parameters for the chevron structure
    total_width = 120.0  # matches footprint constraint
    total_height = 4.0   # matches footprint constraint
    num_waveguides = 5   # number of parallel waveguides
    gap_between_waveguides = total_height / (num_waveguides + 1)
    
    # Create the chevron waveguides
    for i in range(num_waveguides):
        # Calculate y position for each waveguide
        y_position = (i + 1) * gap_between_waveguides
        
        # Create a path with straight segments forming a chevron/V shape
        # Start at left edge, go to center point, then to right edge
        center_x = total_width / 2  # 60.0 um
        center_y = y_position  # maintain same y position for center point
        
        # For the chevron pattern, we need to create a V shape
        # The center point should be slightly offset to create the V
        # Let's make the center point lower for odd-numbered waveguides and higher for even
        # This creates the alternating chevron pattern
        
        if i % 2 == 0:  # Even index (0, 2, 4) - point down
            center_offset = -0.5  # Move center point down
        else:  # Odd index (1, 3) - point up  
            center_offset = 0.5   # Move center point up
            
        center_y = y_position + center_offset
        
        # Create the path with three straight segments
        path_points = [
            (0, y_position),           # start point on left edge
            (center_x, center_y),      # center point (creating the V)
            (total_width, y_position)  # end point on right edge
        ]
        
        # Create the path
        path = gf.Path(path_points)
        
        # Extrude the path to create the waveguide
        waveguide = gf.path.extrude(path, cross_section=xs)
        
        # Add the waveguide to the component
        ref = c << waveguide
        
        # Add ports for external connections
        c.add_port(f"left_{i+1}", port=ref.ports["o1"])
        c.add_port(f"right_{i+1}", port=ref.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")