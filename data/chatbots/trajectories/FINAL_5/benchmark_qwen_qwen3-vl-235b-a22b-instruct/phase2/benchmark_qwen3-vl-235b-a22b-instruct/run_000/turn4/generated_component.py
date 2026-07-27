import gdsfactory as gf

@gf.cell
def directional_coupler_with_grating():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius=10.0)
    
    # Create the two straight waveguides for the directional coupler
    # Top waveguide
    wg1 = c << gf.components.straight(length=18.0, cross_section=xs)
    wg1.move((0, 0.35))  # Position with gap from bottom waveguide
    
    # Bottom waveguide
    wg2 = c << gf.components.straight(length=18.0, cross_section=xs)
    wg2.move((0, -0.35))  # Position with gap from top waveguide
    
    # Create tapers at both ends
    # Left tapers (input side)
    taper_left_top = c << gf.components.taper(length=3.0, width1=0.5, width2=2.0)
    taper_left_bottom = c << gf.components.taper(length=3.0, width1=0.5, width2=2.0)
    
    taper_left_top.move((-3.0, 0.35))
    taper_left_bottom.move((-3.0, -0.35))
    
    # Right tapers (output side)
    taper_right_top = c << gf.components.taper(length=3.0, width1=0.5, width2=2.0)
    taper_right_bottom = c << gf.components.taper(length=3.0, width1=0.5, width2=2.0)
    
    taper_right_top.move((18.0, 0.35))
    taper_right_bottom.move((18.0, -0.35))
    
    # Add ports for connectivity
    c.add_port("o1", port=taper_left_top.ports["o1"])
    c.add_port("o2", port=taper_left_bottom.ports["o1"])
    c.add_port("o3", port=taper_right_top.ports["o2"])
    c.add_port("o4", port=taper_right_bottom.ports["o2"])
    
    return c

# Create and save the device
device = directional_coupler_with_grating()
device.write_gds("directional_coupler_with_grating.gds")