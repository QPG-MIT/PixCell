import gdsfactory as gf

@gf.cell
def recreate_device():
    c = gf.Component()
    
    # Define cross-section for waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create the S-bend components for the left side
    s_bend_left_top = c << gf.components.bend_s(size=(20, 2), cross_section=xs)
    s_bend_left_bottom = c << gf.components.bend_s(size=(20, 2), cross_section=xs)
    s_bend_left_bottom.mirror()
    
    # Create the S-bend components for the right side
    s_bend_right_top = c << gf.components.bend_s(size=(20, 2), cross_section=xs)
    s_bend_right_bottom = c << gf.components.bend_s(size=(20, 2), cross_section=xs)
    s_bend_right_bottom.mirror()
    
    # Create straight sections to connect the S-bends
    straight_length = 80  # Total length minus S-bend sections
    straight_top = c << gf.components.straight(length=straight_length, cross_section=xs)
    straight_bottom = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    # Connect the components
    # Connect left S-bends to straight sections
    s_bend_left_top.connect("o2", straight_top.ports["o1"])
    s_bend_left_bottom.connect("o2", straight_bottom.ports["o1"])
    
    # Connect right S-bends to straight sections
    s_bend_right_top.connect("o1", straight_top.ports["o2"])
    s_bend_right_bottom.connect("o1", straight_bottom.ports["o2"])
    
    # Position the bottom waveguide below the top one
    straight_bottom.movey(-4.0)
    s_bend_left_bottom.movey(-4.0)
    s_bend_right_bottom.movey(-4.0)
    
    # Expose ports for the device
    c.add_port("input_top", port=s_bend_left_top.ports["o1"])
    c.add_port("output_top", port=s_bend_right_top.ports["o2"])
    c.add_port("input_bottom", port=s_bend_left_bottom.ports["o1"])
    c.add_port("output_bottom", port=s_bend_right_bottom.ports["o2"])
    
    return c

# Create and save the device
device = recreate_device()
device.write_gds("recreated_device.gds")