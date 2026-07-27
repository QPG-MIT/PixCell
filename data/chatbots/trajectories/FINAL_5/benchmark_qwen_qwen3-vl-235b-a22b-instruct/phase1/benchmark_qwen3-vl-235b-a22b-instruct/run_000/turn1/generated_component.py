import gdsfactory as gf

@gf.cell
def directional_coupler_with_grating():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the two waveguides with tapers at ends
    # First waveguide (top)
    wg1_taper_in = c << gf.components.taper(length=2.0, width1=0.5, width2=0.1)
    wg1_straight = c << gf.components.straight(length=14.24, cross_section=xs)
    wg1_taper_out = c << gf.components.taper(length=2.0, width1=0.5, width2=0.1)
    
    # Second waveguide (bottom)
    wg2_taper_in = c << gf.components.taper(length=2.0, width1=0.5, width2=0.1)
    wg2_straight = c << gf.components.straight(length=14.24, cross_section=xs)
    wg2_taper_out = c << gf.components.taper(length=2.0, width1=0.5, width2=0.1)
    
    # Position the first waveguide
    wg1_taper_in.move((0, 0.35))
    wg1_straight.move((2.0, 0.35))
    wg1_taper_out.move((16.24, 0.35))
    
    # Position the second waveguide
    wg2_taper_in.move((0, -0.35))
    wg2_straight.move((2.0, -0.35))
    wg2_taper_out.move((16.24, -0.35))
    
    # Create the grating pattern
    grating_period = 0.5
    num_grating_elements = int(14.24 / grating_period)
    
    for i in range(num_grating_elements):
        x_pos = 2.0 + i * grating_period  # Start after taper
        
        # Create small rectangles to represent grating elements
        grating_element_top = c << gf.components.rectangle(size=(0.3, 0.1), layer=(1, 0))
        grating_element_bottom = c << gf.components.rectangle(size=(0.3, 0.1), layer=(1, 0))
        
        grating_element_top.move((x_pos, 0.35))
        grating_element_bottom.move((x_pos, -0.35))
    
    # Add ports for connectivity
    # Use the input ports of the tapers
    c.add_port("o1", port=wg1_taper_in.ports["o1"])
    c.add_port("o2", port=wg1_taper_out.ports["o2"])
    c.add_port("o3", port=wg2_taper_in.ports["o1"])
    c.add_port("o4", port=wg2_taper_out.ports["o2"])
    
    return c

# Create and save the device
device = directional_coupler_with_grating()
device.write_gds("directional_coupler_with_grating.gds")