import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define layer
    layer = (1, 0)
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=layer)
    
    # Define parameters for the curved structure
    total_width = 120.0  # matches footprint constraint
    total_height = 4.0   # matches footprint constraint
    num_waveguides = 5   # number of parallel waveguides
    gap_between_waveguides = total_height / (num_waveguides + 1)
    
    # Create the curved waveguides
    for i in range(num_waveguides):
        # Calculate y position for each waveguide
        y_position = (i + 1) * gap_between_waveguides
        
        # Create a path that curves inward then outward
        path_points = [
            (0, y_position),  # start point
            (20, y_position - 0.5),  # curve inward
            (60, y_position - 1.0),  # maximum pinch
            (100, y_position - 0.5),  # curve outward
            (120, y_position)  # end point
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