import gdsfactory as gf

def simple_vertical_waveguides_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create two parallel vertical waveguides
    # Based on the target image, we need two simple vertical lines
    
    # First waveguide (left side)
    wg1 = c << gf.components.straight(length=120, cross_section=xs)
    wg1.move((0, 0))  # Position at left
    
    # Second waveguide (right side)
    wg2 = c << gf.components.straight(length=120, cross_section=xs)
    wg2.move((5, 0))  # Position at right with some gap
    
    # Add ports for both waveguides
    c.add_port("o1_1", port=wg1.ports["o1"])
    c.add_port("o2_1", port=wg1.ports["o2"])
    c.add_port("o1_2", port=wg2.ports["o1"])
    c.add_port("o2_2", port=wg2.ports["o2"])
    
    return c

# Create and save the device
device = simple_vertical_waveguides_device()
device.write_gds("simple_vertical_waveguides.gds")