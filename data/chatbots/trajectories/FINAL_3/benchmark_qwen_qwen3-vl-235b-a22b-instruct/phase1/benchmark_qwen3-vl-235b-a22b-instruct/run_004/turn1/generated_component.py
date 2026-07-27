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
    
    # Create the top S-bend
    top_s_bend = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    
    # Create the bottom S-bend (mirrored)
    bottom_s_bend = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    bottom_s_bend.mirror()
    
    # Create the top straight section
    top_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    # Create the bottom straight section
    bottom_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    # Position components
    # Top path: top_s_bend -> top_straight -> top_s_bend (mirrored)
    top_s_bend.move((0, 0))
    top_straight.connect("o1", top_s_bend.ports["o2"])
    
    # Create a mirrored version of the top S-bend for the right side
    right_top_s_bend = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    right_top_s_bend.mirror()
    right_top_s_bend.connect("o1", top_straight.ports["o2"])
    
    # Bottom path: bottom_s_bend -> bottom_straight -> bottom_s_bend (mirrored)
    bottom_s_bend.move((0, -(waveguide_width + gap)))
    bottom_straight.connect("o1", bottom_s_bend.ports["o2"])
    
    # Create a mirrored version of the bottom S-bend for the right side
    right_bottom_s_bend = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    right_bottom_s_bend.mirror()
    right_bottom_s_bend.connect("o1", bottom_straight.ports["o2"])
    
    # Add ports
    c.add_port("o1_top", port=top_s_bend.ports["o1"])
    c.add_port("o2_top", port=right_top_s_bend.ports["o2"])
    c.add_port("o1_bottom", port=bottom_s_bend.ports["o1"])
    c.add_port("o2_bottom", port=right_bottom_s_bend.ports["o2"])
    
    return c

# Create and save the device
device = s_bend_coupler()
device.write_gds("s_bend_coupler.gds")