import gdsfactory as gf

@gf.cell
def directional_coupler_with_grating():
    c = gf.Component()
    
    # Define cross-section for waveguides with appropriate minimum radius
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius=10.0)
    
    # Create the two waveguides with S-bends using path system
    # First waveguide (top)
    path1 = gf.Path()
    path1.append(gf.path.straight(length=2.0))  # Taper section
    path1.append(gf.path.straight(length=10.0))  # Straight section
    path1.append(gf.path.euler(radius=10.0, angle=180))  # Half circle for S-bend
    path1.append(gf.path.straight(length=10.0))  # Straight section
    path1.append(gf.path.straight(length=2.0))  # Taper section
    
    # Second waveguide (bottom)
    path2 = gf.Path()
    path2.append(gf.path.straight(length=2.0))  # Taper section
    path2.append(gf.path.straight(length=10.0))  # Straight section
    path2.append(gf.path.euler(radius=10.0, angle=-180))  # Half circle for S-bend
    path2.append(gf.path.straight(length=10.0))  # Straight section
    path2.append(gf.path.straight(length=2.0))  # Taper section
    
    # Extrude paths to create waveguides
    wg1 = c << gf.path.extrude(path1, cross_section=xs)
    wg2 = c << gf.path.extrude(path2, cross_section=xs)
    
    # Position the waveguides
    wg1.move((0, 0.35))
    wg2.move((0, -0.35))
    
    # Create the grating pattern in the middle region
    grating_period = 0.5
    num_grating_elements = int(10.0 / grating_period)
    
    for i in range(num_grating_elements):
        x_pos = 2.0 + i * grating_period  # Start after taper
        
        # Create small rectangles to represent grating elements
        grating_element_top = c << gf.components.rectangle(size=(0.3, 0.1), layer=(1, 0))
        grating_element_bottom = c << gf.components.rectangle(size=(0.3, 0.1), layer=(1, 0))
        
        grating_element_top.move((x_pos, 0.35))
        grating_element_bottom.move((x_pos, -0.35))
    
    # Add ports for connectivity
    c.add_port("o1", port=wg1.ports["o1"])
    c.add_port("o2", port=wg1.ports["o2"])
    c.add_port("o3", port=wg2.ports["o1"])
    c.add_port("o4", port=wg2.ports["o2"])
    
    return c

# Create and save the device
device = directional_coupler_with_grating()
device.write_gds("directional_coupler_with_grating.gds")