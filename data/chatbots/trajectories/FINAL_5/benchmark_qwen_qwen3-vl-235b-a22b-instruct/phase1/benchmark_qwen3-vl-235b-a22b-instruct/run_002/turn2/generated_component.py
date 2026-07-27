import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the S-shaped waveguide path with proper curvature
    # Top arm
    top_path = gf.Path()
    top_path.append(gf.path.straight(length=4.0))
    top_path.append(gf.path.euler(radius=2.0, angle=90, p=0.5))
    top_path.append(gf.path.straight(length=10.0))
    top_path.append(gf.path.euler(radius=2.0, angle=90, p=0.5))
    top_path.append(gf.path.straight(length=4.0))
    
    # Bottom arm
    bottom_path = gf.Path()
    bottom_path.append(gf.path.straight(length=4.0))
    bottom_path.append(gf.path.euler(radius=2.0, angle=-90, p=0.5))
    bottom_path.append(gf.path.straight(length=10.0))
    bottom_path.append(gf.path.euler(radius=2.0, angle=-90, p=0.5))
    bottom_path.append(gf.path.straight(length=4.0))
    
    # Create tapered ends for the waveguides
    # Create a taper component
    taper = gf.components.taper(length=2.0, width1=0.5, width2=0.1)
    
    # Extrude paths to create waveguides
    top_waveguide = gf.path.extrude(top_path, cross_section=xs)
    bottom_waveguide = gf.path.extrude(bottom_path, cross_section=xs)
    
    # Add waveguides to component
    top_ref = c << top_waveguide
    bottom_ref = c << bottom_waveguide
    
    # Position bottom waveguide below top waveguide
    bottom_ref.move((0, -0.7))
    
    # Add tapered ends to both waveguides
    # Top left taper
    top_left_taper = c << taper
    top_left_taper.rotate(180)
    top_left_taper.move((0, 0.25))
    
    # Top right taper
    top_right_taper = c << taper
    top_right_taper.move((18.0, 0.25))
    
    # Bottom left taper
    bottom_left_taper = c << taper
    bottom_left_taper.rotate(180)
    bottom_left_taper.move((0, -0.95))
    
    # Bottom right taper
    bottom_right_taper = c << taper
    bottom_right_taper.move((18.0, -0.95))
    
    # Create grating coupler features in the central region
    # Create small rectangles for the grating elements
    grating_element = gf.components.rectangle(size=(0.1, 0.1), layer=(1, 0))
    
    # Add array of grating elements between the waveguides
    for i in range(40):
        grating_ref = c << grating_element
        grating_ref.move((4.0 + i * 0.2, 0.0))
    
    # Add another row of grating elements below
    for i in range(40):
        grating_ref = c << grating_element
        grating_ref.move((4.0 + i * 0.2, -0.7))
    
    # Add ports for connection
    c.add_port("o1", port=top_ref.ports["o1"])
    c.add_port("o2", port=bottom_ref.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")