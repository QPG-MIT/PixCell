import gdsfactory as gf

@gf.cell
def recreate_angled_waveguide_device():
    c = gf.Component()
    
    # Define cross-section for waveguide
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a path that goes straight, then diagonally, then straight again
    # This will create the angled transition shown in the target image
    points = [
        (0, 0),           # Start point
        (40, 0),          # First straight segment
        (80, -20),        # Diagonal transition (this creates the angle)
        (120, -20)        # Final straight segment
    ]
    
    # Create path with smooth transitions
    path = gf.path.smooth(points=points, radius=5.0)
    
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