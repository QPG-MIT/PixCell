import gdsfactory as gf

@gf.cell
def recreate_angled_waveguide_device():
    c = gf.Component()
    
    # Define cross-section for waveguide
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a simple straight path that's slightly angled
    # The target appears to be a single straight waveguide with a slight diagonal
    points = [
        (0, 0),           # Start point
        (2, 120)          # End point - creating a slight diagonal angle
    ]
    
    # Create straight path (no smoothing needed for this simple case)
    path = gf.Path(points)
    
    # Extrude the path to create the waveguide
    waveguide = gf.path.extrude(path, cross_section=xs)
    
    # Add the waveguide to the component
    ref = c << waveguide
    
    # Add ports at the beginning and end
    c.add_port("o1", port=ref.ports["o1"])
    c.add_port("o2", port=ref.ports["o2"])
    
    return c

# Create and save the device
device = recreate_angled_waveguide_device()
device.write_gds("angled_waveguide_device.gds")