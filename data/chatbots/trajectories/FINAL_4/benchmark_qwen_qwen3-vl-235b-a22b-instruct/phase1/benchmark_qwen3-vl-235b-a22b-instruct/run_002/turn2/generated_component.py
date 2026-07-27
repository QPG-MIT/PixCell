import gdsfactory as gf

@gf.cell
def improved_sinusoidal_waveguide_pair():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the path for the top waveguide with smoother transitions
    # Use more points to create a smoother sinusoidal curve
    top_points = [
        (0, 1.5),      # Start point (straight section)
        (3, 1.5),      # Transition to curve
        (6, 1.0),      # First curve point
        (9, 0.5),      # Middle point (closest approach)
        (12, 1.0),     # Second curve point
        (15, 1.5),     # Transition back to straight
        (18, 1.5)      # End point (straight section)
    ]
    top_path = gf.path.smooth(points=top_points, radius=4.0)
    top_waveguide = gf.path.extrude(top_path, cross_section=xs)
    
    # Create the path for the bottom waveguide (mirrored)
    bottom_points = [
        (0, -1.5),     # Start point (straight section)
        (3, -1.5),     # Transition to curve
        (6, -1.0),     # First curve point
        (9, -0.5),     # Middle point (closest approach)
        (12, -1.0),    # Second curve point
        (15, -1.5),    # Transition back to straight
        (18, -1.5)     # End point (straight section)
    ]
    bottom_path = gf.path.smooth(points=bottom_points, radius=4.0)
    bottom_waveguide = gf.path.extrude(bottom_path, cross_section=xs)
    
    # Add both waveguides to the component
    top_ref = c << top_waveguide
    bottom_ref = c << bottom_waveguide
    
    # Add ports for connectivity
    c.add_port("o1_top", port=top_ref.ports["o1"])
    c.add_port("o2_top", port=top_ref.ports["o2"])
    c.add_port("o1_bottom", port=bottom_ref.ports["o1"])
    c.add_port("o2_bottom", port=bottom_ref.ports["o2"])
    
    return c

# Create and save the device
device = improved_sinusoidal_waveguide_pair()
device.write_gds("improved_sinusoidal_waveguide_pair.gds")