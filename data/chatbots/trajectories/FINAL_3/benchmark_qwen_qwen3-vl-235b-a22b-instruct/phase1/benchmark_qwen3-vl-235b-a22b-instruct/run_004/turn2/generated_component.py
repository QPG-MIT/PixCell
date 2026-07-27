import gdsfactory as gf

@gf.cell
def s_bend_coupler():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Parameters based on footprint (120um x 4um)
    total_length = 120.0
    waveguide_width = 0.5
    gap = 0.5  # gap between waveguides
    s_bend_size = (20, 2)  # S-bend size (dx, dy)
    
    # Calculate straight section length
    straight_length = total_length - 2 * s_bend_size[0]
    
    # Create top waveguide
    top_s_bend_left = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    top_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    top_s_bend_right = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    
    # Connect top waveguide components
    top_s_bend_left.move((0, 0))
    top_straight.connect("o1", top_s_bend_left.ports["o2"])
    top_s_bend_right.connect("o1", top_straight.ports["o2"])
    
    # Create bottom waveguide
    bottom_s_bend_left = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    bottom_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    bottom_s_bend_right = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    
    # Position bottom waveguide - this is the key fix
    # The bottom waveguide should be positioned such that it's symmetric with the top
    # The gap should be between the two waveguides
    bottom_s_bend_left.move((0, -(waveguide_width + gap)))
    bottom_straight.connect("o1", bottom_s_bend_left.ports["o2"])
    bottom_s_bend_right.connect("o1", bottom_straight.ports["o2"])
    
    # Add ports
    c.add_port("o1_top", port=top_s_bend_left.ports["o1"])
    c.add_port("o2_top", port=top_s_bend_right.ports["o2"])
    c.add_port("o1_bottom", port=bottom_s_bend_left.ports["o1"])
    c.add_port("o2_bottom", port=bottom_s_bend_right.ports["o2"])
    
    return c

# Create and save the device
device = s_bend_coupler()
device.write_gds("s_bend_coupler.gds")