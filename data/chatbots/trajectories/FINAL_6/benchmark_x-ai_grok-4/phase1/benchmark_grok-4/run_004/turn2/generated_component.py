import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)
    
    # Parameters
    arm_length = 4.7 / 2
    w_wide = 2.0
    w_tip = 0.001
    
    # Cross sections
    xs_wide = gf.cross_section.cross_section(width=w_wide, layer=layer)
    xs_tip = gf.cross_section.cross_section(width=w_tip, layer=layer)
    
    # Arm component
    arm = gf.Component("arm")
    
    # Single segment: transition from wide to tip
    trans = gf.path.transition(xs_wide, xs_tip, width_type='parabolic')
    path = gf.path.straight(length=arm_length)
    segment = gf.path.extrude_transition(path, trans)
    arm << segment
    
    # Add arms to main component
    right = c << arm
    
    left = c << arm
    left.rotate(180)
    
    up = c << arm
    up.rotate(90)
    
    down = c << arm
    down.rotate(270)
    
    return c

device = my_device()
device.write_gds("my_device.gds")