import gdsfactory as gf

@gf.cell
def finger():
    layer = (1, 0)
    xs_wide = gf.cross_section.cross_section(width=12.5, layer=layer)
    xs_narrow = gf.cross_section.cross_section(width=0.01, layer=layer)
    p = gf.path.straight(length=5)
    tr = gf.path.transition(xs_wide, xs_narrow, width_type='linear')
    t = gf.path.extrude_transition(p, tr)
    f = gf.Component()
    t_ref = f << t
    return f

@gf.cell
def my_device():
    layer = (1, 0)

    # Bottom taper positioned
    btaper_c = gf.Component()
    xs_wide = gf.cross_section.cross_section(width=25, layer=layer)
    xs_narrow = gf.cross_section.cross_section(width=0.01, layer=layer)
    p = gf.path.straight(length=5)
    tr = gf.path.transition(xs_wide, xs_narrow, width_type='linear')
    bt = gf.path.extrude_transition(p, tr)
    bt_ref = btaper_c << bt
    bt_ref.rotate(-90)
    bt_ref.move((0, 0), (12.5, 5))

    # Start with bottom taper
    combined = btaper_c

    # Four fingers positioned and unioned one by one
    centers = [6.25, 10.416666666666666, 14.583333333333334, 18.75]
    for xc in centers:
        finger_c = gf.Component()
        fg = finger()
        fg_ref = finger_c << fg
        fg_ref.rotate(90)
        fg_ref.move((0, 0), (xc, 5))
        combined = gf.boolean(combined, finger_c, operation="or", layer=layer)

    return combined

device = my_device()
device.write_gds("my_device.gds")