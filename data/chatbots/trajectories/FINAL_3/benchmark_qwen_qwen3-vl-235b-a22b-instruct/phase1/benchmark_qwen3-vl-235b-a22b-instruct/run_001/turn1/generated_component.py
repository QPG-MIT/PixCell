import gdsfactory as gf

@gf.cell
def recreate_s_bend_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create central straight sections
    # We need to determine appropriate lengths for straight sections and S-bends
    # Given total footprint is 120um, we'll allocate space for S-bends and straight sections
    
    # Create S-bend components
    # S-bend parameters: size=(dx, dy) where dx is horizontal distance, dy is vertical offset
    # For our symmetric design, we want S-bends that connect the parallel waveguides
    s_bend_size = (20, 2)  # dx=20um, dy=2um (vertical offset between waveguides)
    s_bend_top = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    s_bend_bottom = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    
    # Create straight waveguide sections
    # Calculate straight length: total 120um minus S-bend lengths
    # Each S-bend has dx=20um, so we need 120 - 2*20 = 80um for straight sections
    straight_length = 80
    straight_top = c << gf.components.straight(length=straight_length, cross_section=xs)
    straight_bottom = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    # Position the components
    # First, place the top S-bend at origin
    s_bend_top.move((0, 0))
    
    # Connect the straight section to the top S-bend
    straight_top.connect("o1", s_bend_top.ports["o2"])
    
    # Place the bottom S-bend mirrored below
    s_bend_bottom.move((0, -2))  # Move down by the dy value
    s_bend_bottom.mirror()  # Mirror to create the bottom S-bend pattern
    
    # Connect the bottom straight section
    straight_bottom.connect("o1", s_bend_bottom.ports["o2"])
    
    # Now connect the other ends of the S-bends
    # Create mirrored S-bends for the right side
    s_bend_top_right = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    s_bend_bottom_right = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    
    # Position right S-bends
    s_bend_top_right.connect("o1", straight_top.ports["o2"])
    s_bend_bottom_right.connect("o1", straight_bottom.ports["o2"])
    s_bend_bottom_right.mirror()
    
    # Expose external ports
    c.add_port("o1_top", port=s_bend_top.ports["o1"])
    c.add_port("o2_top", port=s_bend_top_right.ports["o2"])
    c.add_port("o1_bottom", port=s_bend_bottom.ports["o1"])
    c.add_port("o2_bottom", port=s_bend_bottom_right.ports["o2"])
    
    return c

# Create and save the device
device = recreate_s_bend_device()
device.write_gds("s_bend_device.gds")