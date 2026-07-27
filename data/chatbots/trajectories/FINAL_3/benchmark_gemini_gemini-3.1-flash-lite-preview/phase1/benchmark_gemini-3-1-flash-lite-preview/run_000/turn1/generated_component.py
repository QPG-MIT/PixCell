import gdsfactory as gf

@gf.cell
def custom_directional_coupler():
    """
    Recreates the waveguide coupler structure from primitives.
    Length: 120um, Height: 4um.
    """
    c = gf.Component("coupler_structure")
    
    # 1. Define Cross Section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    
    # 2. Define Parameters
    # Total Length = 120um
    # We distribute length as: 15 (in) + 45 (bend) + 0 (middle) + 45 (bend) + 15 (out)
    l_in = 15
    l_bend = 45
    
    # Y-offsets (for 4um footprint)
    y_input = 2.0
    y_coupling = 0.5
    dy = y_input - y_coupling # 1.5um shift per bend
    
    # 3. Create a single waveguide arm function
    def create_arm(start_y, dy_val, flip_bend=False):
        arm = gf.Component()
        
        # Determine bend direction
        bend_y = -dy_val if not flip_bend else dy_val
        
        # Assemble sequence
        # Start straight
        w1 = arm << gf.components.straight(length=l_in, cross_section=xs)
        
        # First S-bend (Moving towards center)
        b1 = arm << gf.components.bend_s(size=(l_bend, bend_y), cross_section=xs)
        b1.connect("o1", w1.ports["o2"])
        
        # Second S-bend (Moving away from center)
        b2 = arm << gf.components.bend_s(size=(l_bend, -bend_y), cross_section=xs)
        b2.connect("o1", b1.ports["o2"])
        
        # End straight
        w2 = arm << gf.components.straight(length=l_in, cross_section=xs)
        w2.connect("o1", b2.ports["o2"])
        
        # Expose ports
        arm.add_port("o1", port=w1.ports["o1"])
        arm.add_port("o2", port=w2.ports["o2"])
        
        return arm

    # 4. Assemble Top and Bottom Arms
    # Top arm (bends down then up)
    top_arm = c << create_arm(start_y=y_input, dy_val=dy, flip_bend=False)
    top_arm.movey(y_input)
    
    # Bottom arm (bends up then down - mirrored relative to center)
    bot_arm = c << create_arm(start_y=-y_input, dy_val=dy, flip_bend=True)
    bot_arm.movey(-y_input)
    
    # 5. Add Port references
    c.add_port("o1", port=top_arm.ports["o1"])
    c.add_port("o2", port=bot_arm.ports["o1"])
    c.add_port("o3", port=top_arm.ports["o2"])
    c.add_port("o4", port=bot_arm.ports["o2"])
    
    return c

# Generate the device
device = custom_directional_coupler()

# Save/Show
# device.show() 
device.write_gds("coupler_device.gds")