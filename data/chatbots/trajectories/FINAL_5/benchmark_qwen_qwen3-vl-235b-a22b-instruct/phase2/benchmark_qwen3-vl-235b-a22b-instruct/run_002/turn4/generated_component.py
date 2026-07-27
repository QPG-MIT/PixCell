import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the S-shaped waveguide path
    s_path = gf.Path()
    s_path.append(gf.path.straight(length=4.0))  # Start straight section
    s_path.append(gf.path.euler(radius=2.0, angle=90, p=0.5))  # First bend
    s_path.append(gf.path.straight(length=10.0))  # Central straight section (grating region)
    s_path.append(gf.path.euler(radius=2.0, angle=-90, p=0.5))  # Second bend
    s_path.append(gf.path.straight(length=4.0))  # End straight section
    
    # Create a width transition for tapering the waveguides
    # Start with 0.5um width and taper to 0.1um at the ends
    taper_transition = gf.path.transition(
        gf.cross_section.cross_section(width=0.5, layer=(1, 0)),
        gf.cross_section.cross_section(width=0.1, layer=(1, 0)),
        width_type='linear'
    )
    
    # Extrude the path with tapering
    waveguide = gf.path.extrude_transition(s_path, taper_transition)
    
    # Add waveguide to component
    waveguide_ref = c << waveguide
    
    # Create grating elements - these should be part of the central section
    # Instead of adding separate rectangles, we'll create a grating pattern
    # by adding small rectangles along the central straight section
    
    # Create small rectangles for the grating elements
    grating_element = gf.components.rectangle(size=(0.1, 0.1), layer=(1, 0))
    
    # Add array of grating elements in the central region
    # Position them along the central straight section (from x=4.0 to x=14.0)
    for i in range(40):
        grating_ref = c << grating_element
        grating_ref.move((4.0 + i * 0.2, 0.0))
    
    # Add ports for connection
    c.add_port("o1", port=waveguide_ref.ports["o1"])
    c.add_port("o2", port=waveguide_ref.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")