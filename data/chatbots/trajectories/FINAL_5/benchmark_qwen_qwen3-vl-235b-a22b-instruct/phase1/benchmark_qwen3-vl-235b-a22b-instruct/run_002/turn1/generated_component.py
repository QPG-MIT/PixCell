import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the S-shaped waveguide path
    # Top arm
    top_path = gf.Path()
    top_path.append(gf.path.straight(length=5.0))
    top_path.append(gf.path.euler(radius=3.0, angle=90, p=0.5))
    top_path.append(gf.path.straight(length=8.0))
    top_path.append(gf.path.euler(radius=3.0, angle=90, p=0.5))
    top_path.append(gf.path.straight(length=5.0))
    
    # Bottom arm (mirror of top arm)
    bottom_path = gf.Path()
    bottom_path.append(gf.path.straight(length=5.0))
    bottom_path.append(gf.path.euler(radius=3.0, angle=-90, p=0.5))
    bottom_path.append(gf.path.straight(length=8.0))
    bottom_path.append(gf.path.euler(radius=3.0, angle=-90, p=0.5))
    bottom_path.append(gf.path.straight(length=5.0))
    
    # Extrude paths to create waveguides
    top_waveguide = gf.path.extrude(top_path, cross_section=xs)
    bottom_waveguide = gf.path.extrude(bottom_path, cross_section=xs)
    
    # Add waveguides to component
    top_ref = c << top_waveguide
    bottom_ref = c << bottom_waveguide
    
    # Position bottom waveguide below top waveguide
    bottom_ref.move((0, -0.7))
    
    # Create grating coupler features in the central region
    # Create a rectangle for the central region
    central_region = gf.components.rectangle(size=(8.0, 0.1), layer=(1, 0))
    central_ref = c << central_region
    central_ref.move((5.0, -0.05))  # Position in the center
    
    # Create grating elements (small rectangles)
    grating_element = gf.components.rectangle(size=(0.2, 0.1), layer=(1, 0))
    
    # Add array of grating elements
    for i in range(40):  # Adjust number based on image
        grating_ref = c << grating_element
        grating_ref.move((5.0 + i * 0.2, 0.0))
    
    # Add another row of grating elements below
    for i in range(40):
        grating_ref = c << grating_element
        grating_ref.move((5.0 + i * 0.2, -0.7))
    
    # Add ports for connection
    c.add_port("o1", port=top_ref.ports["o1"])
    c.add_port("o2", port=bottom_ref.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")