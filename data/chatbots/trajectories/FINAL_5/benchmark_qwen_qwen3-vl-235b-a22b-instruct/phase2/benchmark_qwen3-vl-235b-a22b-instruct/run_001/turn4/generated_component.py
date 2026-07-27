import gdsfactory as gf

@gf.cell
def create_simple_waveguide_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(
        width=0.7,  # Use the full width of the footprint
        layer=(1, 0),
        radius=10.0,
        radius_min=10.0
    )
    
    # Create the central straight waveguide
    central_length = 18.24  # Matches the footprint constraint
    central_width = 0.7     # Matches the footprint constraint
    
    # Create central straight waveguide
    central_waveguide = c << gf.components.straight(
        length=central_length, 
        cross_section=xs
    )
    
    # Add ports at the ends of the waveguide
    c.add_port("o1", port=central_waveguide.ports["o1"])
    c.add_port("o2", port=central_waveguide.ports["o2"])
    
    return c

# Create and save the device
device = create_simple_waveguide_device()
device.write_gds("simple_waveguide_device.gds")