import gdsfactory as gf

def bezier_points(control_points, npoints=101):
    points = []
    for i in range(npoints):
        t = i / (npoints - 1.0)
        t1 = 1 - t
        x = (t1**3 * control_points[0][0] + 
             3 * t1**2 * t * control_points[1][0] + 
             3 * t1 * t**2 * control_points[2][0] + 
             t**3 * control_points[3][0])
        y = (t1**3 * control_points[0][1] + 
             3 * t1**2 * t * control_points[1][1] + 
             3 * t1 * t**2 * control_points[2][1] + 
             t**3 * control_points[3][1])
        x = round(x * 1000) / 1000.0
        y = round(y * 1000) / 1000.0
        points.append((x, y))
    return points

@gf.cell
def bend_s_custom(dx, dy, width1, width2=None, width_type='linear', layer=(1, 0)):
    control_points = [(0, 0), (dx / 2, 0), (dx / 2, dy), (dx, dy)]
    points = bezier_points(control_points)
    p = gf.Path(points)
    if width2 is not None:
        cs1 = gf.cross_section.cross_section(width=width1, layer=layer)
        cs2 = gf.cross_section.cross_section(width=width2, layer=layer)
        transition = gf.path.transition(cs1, cs2, width_type=width_type)
        return gf.path.extrude_transition(p, transition)
    else:
        cs = gf.cross_section.cross_section(width=width1, layer=layer)
        return gf.path.extrude(p, cs)

@gf.cell
def s_dip(half_length, offset, straight_length, w_narrow, w_wide, layer=(1, 0)):
    c = gf.Component()
    b1 = c << bend_s_custom(half_length, -offset, width1=w_narrow, width2=w_wide, width_type='sine', layer=layer)
    if straight_length > 0:
        p_strt = gf.path.straight(length=straight_length)
        cs = gf.cross_section.cross_section(width=w_wide, layer=layer)
        strt = gf.path.extrude(p_strt, cs)
        s = c << strt
        s.connect("o1", b1.ports["o2"])
        last = s
    else:
        last = b1
    b2 = c << bend_s_custom(half_length, offset, width1=w_wide, width2=w_narrow, width_type='sine', layer=layer)
    b2.connect("o1", last.ports["o2"])
    c.add_port("o1", port=b1.ports["o1"])
    c.add_port("o2", port=b2.ports["o2"])
    return c

@gf.cell
def device():
    c = gf.Component()

    w_narrow = 0.5
    g_min = 0.2
    d_initial = 3 - w_narrow
    w_wide = 1.4
    c_min = w_wide + g_min
    offset = (d_initial - c_min) / 2
    y_shift = d_initial / 2
    straight_length = 8.0
    half_length = (18.0 - straight_length) / 2
    layer = (1, 0)

    dip = s_dip(half_length, offset, straight_length, w_narrow, w_wide, layer)

    top = c << dip
    top.move((0, y_shift))

    bot = c << dip
    bot.mirror(p1=(0, 0), p2=(1, 0))
    bot.move((0, -y_shift))

    c.add_port("top_left", port=top.ports["o1"])
    c.add_port("top_right", port=top.ports["o2"])
    c.add_port("bot_left", port=bot.ports["o1"])
    c.add_port("bot_right", port=bot.ports["o2"])

    return c

dev = device()
dev.write_gds("my_device.gds")