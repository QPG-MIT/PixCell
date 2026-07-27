import gdsfactory as gf

@gf.cell
def s_bend_coupler():
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Create straight waveguide segments (central part)
    # Total length is 120μm, S-bends will take up some space
    # Estimate S-bend size based on typical parameters
    straight_length = 80  # This will be adjusted based on S-bend size
    
    # Create S-bend components
    # S-bend size should be chosen to fit within the 120μm total length
    # Using size=(20, 2) for dx, dy - this creates a moderate S-bend
    s_bend_top = c << gf.components.bend_s(size=(20, 2), cross_section=xs)
    s_bend_bottom = c << gf.components.bend_s(size=(20, 2), cross_section=xs)
    
    # Create straight waveguides
    straight_top = c << gf.components.straight(length=straight_length, cross_section=xs)
    straight_bottom = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    # Position the components
    # Place top S-bend at origin
    s_bend_top.move((0, 0))
    
    # Connect straight top to top S-bend
    straight_top.connect("o1", s_bend_top.ports["o2"])
    
    # Place bottom S-bend mirrored below
    s_bend_bottom.move((0, -4))  # 4μm separation between centers
    s_bend_bottom.mirror_y()
    
    # Connect straight bottom to bottom S-bend
    straight_bottom.connect("o1", s_bend_bottom.ports["o2"])
    
    # Expose ports
    c.add_port("o1_top", port=s_bend_top.ports["o1"])
    c.add_port("o2_top", port=straight_top.ports["o2"])
    c.add_port("o1_bottom", port=s_bend_bottom.ports["o1"])
    c.add_port("o2_bottom", port=straight_bottom.ports["o2"])
    
    return c

# Create and save the device
device = s_bend_coupler()
device.write_gds("s_bend_coupler.gds")