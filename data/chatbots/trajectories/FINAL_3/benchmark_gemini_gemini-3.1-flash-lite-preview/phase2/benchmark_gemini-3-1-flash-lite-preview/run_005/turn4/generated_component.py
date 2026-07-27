import gdsfactory as gf

@gf.cell
def arm_section():
    """Constructs one half of the symmetric coupler."""
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # Arm layout: Straight -> Bend_S -> Straight -> Bend_S -> Straight
    # The bend_s shifts the waveguide by 1.75um vertically over 20um.
    
    s_left = c << gf.components.straight(length=20, cross_section=xs)
    trans1 = c << gf.components.bend_s(size=(20, -1.75), cross_section=xs)
    s_mid = c << gf.components.straight(length=20, cross_section=xs)
    trans2 = c << gf.components.bend_s(size=(20, 1.75), cross_section=xs)
    s_right = c << gf.components.straight(length=20, cross_section=xs)
    
    # Connect the components in sequence
    trans1.connect("o1", s_left.ports["o2"])
    s_mid.connect("o1", trans1.ports["o2"])
    trans2.connect("o1", s_mid.ports["o2"])
    s_right.connect("o1", trans2.ports["o2"])
    
    # Expose ports for the coupler assembly
    c.add_port("o1", port=s_left.ports["o1"])
    c.add_port("o2", port=s_right.ports["o2"])
    
    return c

@gf.cell
def symmetric_coupler():
    """Assembles two mirrored arms to form the final coupler."""
    c = gf.Component()
    
    top = c << arm_section()
    bot = c << arm_section()
    
    # Position the top arm at y=2. The S-bend shifts it to y=0.25 in the center.
    top.movey(2)
    
    # Mirror the bottom arm to flip its bend direction, then position at y=-2.
    # The S-bend shift will move it to y=-0.25 in the center.
    # The resulting gap in the center is 0.25 - (-0.25) = 0.5um.
    bot.mirror() 
    bot.movey(-2)
    
    # Expose external ports
    c.add_port("in1", port=top.ports["o1"])
    c.add_port("in2", port=bot.ports["o1"])
    c.add_port("out1", port=top.ports["o2"])
    c.add_port("out2", port=bot.ports["o2"])
    
    return c

# Create and save
device = symmetric_coupler()
device.write_gds("symmetric_coupler.gds")