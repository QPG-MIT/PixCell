import gdsfactory as gf

@gf.cell
def recreate_s_bend_device():
    c = gf.Component()
    
    # Define cross-section for waveguide
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a smooth path that matches the target shape
    # Start straight, then curve down, then straight again
    points = [
        (0, 0),           # Start point
        (30, 0),          # First straight segment
        (60, -2),         # Curve down
        (90, -2),         # Continue at lower level
        (120, -2)         # End point
    ]
    
    # Create path with smooth transitions
    path = gf.path.smooth(points=points, radius=10.0)
    
    # Extrude the path to create the waveguide
    waveguide = gf.path.extrude(path, cross_section=xs)
    
    # Add the waveguide to the component
    ref = c << waveguide
    
    # Add ports at the beginning and end
    c.add_port("o1", port=ref.ports["o1"])
    c.add_port("o2", port=ref.ports["o2"])
    
    return c

# Create and save the device
device = recreate_s_bend_device()
device.write_gds("s_bend_device.gds")