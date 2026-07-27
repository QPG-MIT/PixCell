import gdsfactory as gf

@gf.cell
def arm_section():
    """Constructs one half of the symmetric coupler."""
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # 1. Start with a bend to shift from the outer position to the inner coupling position
    # (20, -2) shifts the waveguide down by 2um over 20um length
    s1 = c << gf.components.bend_s(size=(20, -2), cross_section=xs)
    
    # 2. Central parallel straight section
    mid = c << gf.components.straight(length=30, cross_section=xs)
    
    # 3. Second bend to shift back out
    # (20, 2) shifts back up by 2um
    s2 = c << gf.components.bend_s(size=(20, 2), cross_section=xs)
    
    # 4. Connect the components
    mid.connect("o1", s1.ports["o2"])
    s2.connect("o1", mid.ports["o2"])
    
    # Expose ports for the component assembly
    c.add_port("o1", port=s1.ports["o1"])
    c.add_port("o2", port=s2.ports["o2"])
    
    return c

@gf.cell
def symmetric_coupler():
    c = gf.Component()
    
    # Create the two arms
    top_arm = c << arm_section()
    bottom_arm = c << arm_section()
    
    # Mirror the bottom arm to create symmetry and move it to create the gap
    bottom_arm.mirror((1, 0)) 
    bottom_arm.movey(-4) # Adjust gap between arms
    top_arm.movey(4)
    
    # Expose external ports
    c.add_port("in1", port=top_arm.ports["o1"])
    c.add_port("in2", port=bottom_arm.ports["o1"])
    c.add_port("out1", port=top_arm.ports["o2"])
    c.add_port("out2", port=bottom_arm.ports["o2"])
    
    return c

# Create and save
device = symmetric_coupler()
device.write_gds("symmetric_coupler.gds")