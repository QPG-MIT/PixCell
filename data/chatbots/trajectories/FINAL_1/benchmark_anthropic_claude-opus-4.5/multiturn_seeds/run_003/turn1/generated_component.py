import gdsfactory as gf

@gf.cell
def optical_tweezers():
    """
    Creates a tweezers-shaped optical coupler/combiner.
    Two waveguides that converge from left to right.
    Footprint: 40 um x 1.7 um
    """
    c = gf.Component()
    
    # Cross-section parameters
    wg_width = 0.15
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # Waveguide path positions (from centerline)
    y_input = 0.68    # Separation at input (left side) - wider apart
    y_output = 0.18   # Separation at output (right side) - close together
    
    # Define path waypoints for smooth S-bend transition
    # Upper waveguide path
    upper_points = [
        (0, y_input),      # Input port
        (8, y_input),      # Straight input section
        (32, y_output),    # After S-bend transition
        (40, y_output)     # Output port
    ]
    
    # Lower waveguide path (mirror of upper)
    lower_points = [
        (0, -y_input),
        (8, -y_input),
        (32, -y_output),
        (40, -y_output)
    ]
    
    # Create smooth paths with appropriate bend radius
    bend_radius = 8
    path_upper = gf.path.smooth(points=upper_points, radius=bend_radius)
    path_lower = gf.path.smooth(points=lower_points, radius=bend_radius)
    
    # Extrude paths to create waveguide components
    wg_upper = gf.path.extrude(path_upper, cross_section=xs)
    wg_lower = gf.path.extrude(path_lower, cross_section=xs)
    
    # Add references to component
    ref_upper = c.add_ref(wg_upper)
    ref_lower = c.add_ref(wg_lower)
    
    # Add ports for external connections
    c.add_port("o1", port=ref_upper.ports["o1"])  # Upper left input
    c.add_port("o2", port=ref_lower.ports["o1"])  # Lower left input
    c.add_port("o3", port=ref_upper.ports["o2"])  # Upper right output
    c.add_port("o4", port=ref_lower.ports["o2"])  # Lower right output
    
    return c


# Create and save the device
device = optical_tweezers()
device.write_gds("optical_tweezers.gds")