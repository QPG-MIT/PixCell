import gdsfactory as gf

@gf.cell
def sinusoidal_waveguide_pair():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the S-bend path for the top waveguide
    # Using smooth path with waypoints to create the sinusoidal shape
    top_points = [(0, 1.5), (6, 1.5), (9, 0.5), (12, 1.5), (18, 1.5)]
    top_path = gf.path.smooth(points=top_points, radius=2.0)
    top_waveguide = gf.path.extrude(top_path, cross_section=xs)
    
    # Create the S-bend path for the bottom waveguide (mirrored)
    bottom_points = [(0, -1.5), (6, -1.5), (9, -0.5), (12, -1.5), (18, -1.5)]
    bottom_path = gf.path.smooth(points=bottom_points, radius=2.0)
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
device = sinusoidal_waveguide_pair()
device.write_gds("sinusoidal_waveguide_pair.gds")