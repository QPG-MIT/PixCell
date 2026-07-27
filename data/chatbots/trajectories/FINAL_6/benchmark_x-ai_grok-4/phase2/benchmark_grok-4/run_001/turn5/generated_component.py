import gdsfactory as gf

@gf.cell
def my_device():
    a = 2.35
    wide = 1.0
    narrow = 0.3
    layer = (1, 0)
    xs_wide = gf.cross_section.cross_section(width=wide, layer=layer)
    xs_narrow = gf.cross_section.cross_section(width=narrow, layer=layer)
    trans = gf.path.transition(xs_wide, xs_narrow, width_type='linear')
    path = gf.path.straight(length=a)
    arm = gf.path.extrude_transition(path, trans)

    # Create individual components for each direction
    c_right = gf.Component()
    ref_right = c_right << arm

    c_left = gf.Component()
    ref_left = c_left << arm
    ref_left.mirror((0, 0), (0, 1))

    c_up = gf.Component()
    ref_up = c_up << arm
    ref_up.rotate(90)

    c_down = gf.Component()
    ref_down = c_down << arm
    ref_down.rotate(-90)

    u1 = gf.boolean(c_right, c_up, "or", layer=layer)
    u2 = gf.boolean(u1, c_left, "or", layer=layer)
    u3 = gf.boolean(u2, c_down, "or", layer=layer)
    return u3

device = my_device()
device.write_gds("my_device.gds")