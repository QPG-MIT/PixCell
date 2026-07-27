import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the top waveguide path with proper curvature and tapering
    top_path = gf.Path()
    top_path.append(gf.path.straight(length=4.0))
    top_path.append(gf.path.euler(radius=2.0, angle=90, p=0.5))
    top_path.append(gf.path.straight(length=10.0))
    top_path.append(gf.path.euler(radius=2.0, angle=90, p=0.5))
    top_path.append(gf.path.straight(length=4.0))
    
    # Create the bottom waveguide path with proper curvature and tapering
    bottom_path = gf.Path()
    bottom_path.append(gf.path.straight(length=4.0))
    bottom_path.append(gf.path.euler(radius=2.0, angle=-90, p=0.5))
    bottom_path.append(gf.path.straight(length=10.0))
    bottom_path.append(gf.path.euler(radius=2.0, angle=-90, p=0.5))
    bottom_path.append(gf.path.straight(length=4.0))
    
    # Create a width transition for tapering the waveguides
    # Start with 0.5um width and taper to 0.1um at the end
    taper_transition = gf.path.transition(
        gf.cross_section.cross_section(width=0.5, layer=(1, 0)),
        gf.cross_section.cross_section(width=0.1, layer=(1, 0)),
        width_type='linear'
    )
    
    # Extrude paths with tapering
    top_waveguide = gf.path.extrude_transition(top_path, taper_transition)
    bottom_waveguide = gf.path.extrude_transition(bottom_path, taper_transition)
    
    # Add waveguides to component
    top_ref = c << top_waveguide
    bottom_ref = c << bottom_waveguide
    
    # Position bottom waveguide below top waveguide
    bottom_ref.move((0, -0.7))
    
    # Create grating coupler features in the central region
    # Create small rectangles for the grating elements
    grating_element = gf.components.rectangle(size=(0.1, 0.1), layer=(1, 0))
    
    # Add array of grating elements in the central region of top waveguide
    for i in range(40):
        grating_ref = c << grating_element
        grating_ref.move((4.0 + i * 0.2, 0.0))
    
    # Add another row of grating elements in the central region of bottom waveguide
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