import gdsfactory as gf

@gf.cell
def directional_coupler_with_grating():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius=10.0)
    
    # Create the two waveguides with tapers and straight sections
    # First waveguide (top)
    path1 = gf.Path()
    path1.append(gf.path.straight(length=5.0))  # Straight section
    path1.append(gf.path.straight(length=8.0))  # Straight section for coupling region
    
    # Second waveguide (bottom)
    path2 = gf.Path()
    path2.append(gf.path.straight(length=5.0))  # Straight section
    path2.append(gf.path.straight(length=8.0))  # Straight section for coupling region
    
    # Extrude paths to create waveguides
    wg1 = c << gf.path.extrude(path1, cross_section=xs)
    wg2 = c << gf.path.extrude(path2, cross_section=xs)
    
    # Position the waveguides with small gap in the coupling region
    wg1.move((0, 0.35))
    wg2.move((0, -0.35))
    
    # Create the tapered ends (matching the target image)
    # Top taper
    taper_top = c << gf.components.taper(length=3.0, width1=0.5, width2=2.0)
    taper_top.move((8.0, 0.35))
    taper_top.rotate(180)
    
    # Bottom taper
    taper_bottom = c << gf.components.taper(length=3.0, width1=0.5, width2=2.0)
    taper_bottom.move((8.0, -0.35))
    taper_bottom.rotate(180)
    
    # Create grating structure in the middle region (simplified version)
    # For a more realistic grating, we would need to implement a more complex pattern
    # But for now, let's create a simplified version that matches the target
    grating_length = 8.0
    grating_period = 0.5
    num_grating_elements = int(grating_length / grating_period)
    
    # Create a more continuous grating structure
    for i in range(num_grating_elements):
        x_pos = 5.0 + i * grating_period  # Start after the initial straight section
        
        # Create small rectangles to represent grating elements
        grating_element_top = c << gf.components.rectangle(size=(0.3, 0.1), layer=(1, 0))
        grating_element_bottom = c << gf.components.rectangle(size=(0.3, 0.1), layer=(1, 0))
        
        grating_element_top.move((x_pos, 0.35))
        grating_element_bottom.move((x_pos, -0.35))
    
    # Add ports for connectivity
    c.add_port("o1", port=wg1.ports["o1"])
    c.add_port("o2", port=taper_top.ports["o2"])
    c.add_port("o3", port=wg2.ports["o1"])
    c.add_port("o4", port=taper_bottom.ports["o2"])
    
    return c

# Create and save the device
device = directional_coupler_with_grating()
device.write_gds("directional_coupler_with_grating.gds")