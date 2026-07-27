import gdsfactory as gf

@gf.cell
def recreate_s_bend_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Total length is 120um
    # Use S-bends with dx=30um each, leaving 60um for straight sections
    s_bend_size = (30, 2)  # (dx, dy)
    straight_length = 60
    
    # Create top waveguide: left S-bend + straight + right S-bend
    top_left_s_bend = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    top_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    top_right_s_bend = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    
    # Create bottom waveguide: left S-bend + straight + right S-bend
    bottom_left_s_bend = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    bottom_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    bottom_right_s_bend = c << gf.components.bend_s(size=s_bend_size, cross_section=xs)
    
    # Position top waveguide
    top_left_s_bend.move((0, 0))
    top_straight.connect("o1", top_left_s_bend.ports["o2"])
    top_right_s_bend.connect("o1", top_straight.ports["o2"])
    
    # Position bottom waveguide (mirrored and offset)
    bottom_left_s_bend.move((0, -2))  # Move down by 2um
    bottom_left_s_bend.mirror()  # Mirror to create bottom S-bend
    bottom_straight.connect("o1", bottom_left_s_bend.ports["o2"])
    bottom_right_s_bend.connect("o1", bottom_straight.ports["o2"])
    bottom_right_s_bend.mirror()
    
    # Expose external ports
    c.add_port("o1_top", port=top_left_s_bend.ports["o1"])
    c.add_port("o2_top", port=top_right_s_bend.ports["o2"])
    c.add_port("o1_bottom", port=bottom_left_s_bend.ports["o1"])
    c.add_port("o2_bottom", port=bottom_right_s_bend.ports["o2"])
    
    return c

# Create and save the device
device = recreate_s_bend_device()
device.write_gds("s_bend_device.gds")