import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguide
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create a straight waveguide path (not S-shaped)
    straight_path = gf.Path()
    straight_path.append(gf.path.straight(length=18.24))  # Match the footprint width
    
    # Create the waveguide component
    waveguide = gf.path.extrude(straight_path, cross_section=xs)
    waveguide_ref = c << waveguide
    
    # Create grating elements - small rectangles along the waveguide
    grating_element = gf.components.rectangle(size=(0.1, 0.1), layer=(1, 0))
    
    # Add array of grating elements along the waveguide
    # Position them along the entire length of the waveguide
    for i in range(91):  # 91 elements to cover 18.24um with 0.2um spacing
        grating_ref = c << grating_element
        grating_ref.move((i * 0.2, 0.0))  # Position along the centerline
    
    # Add ports for connection
    c.add_port("o1", port=waveguide_ref.ports["o1"])
    c.add_port("o2", port=waveguide_ref.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")