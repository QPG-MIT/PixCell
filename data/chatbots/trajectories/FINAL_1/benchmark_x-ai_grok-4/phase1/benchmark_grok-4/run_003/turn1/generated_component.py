import gdsfactory as gf

layer = (1, 0)

def get_xs(w: float):
    return gf.cross_section.cross_section(width=w, layer=layer)

@gf.cell
def device():
    c = gf.Component()

    # Parameters
    thin_width = 0.1
    max_width = 0.4
    length_straight_left = 2.0
    length_taper_wide = 8.0
    length_taper_point_left = 8.0
    gap = 0.5
    l_in = 2.0
    dx_curved = 14.5
    l_end = 5.0
    dy = 0.85 - max_width / 2  # 0.65
    min_width = 0.001

    xs_thin = get_xs(thin_width)
    xs_max = get_xs(max_width)
    xs_point = get_xs(min_width)

    # Left part
    p1 = gf.path.straight(length=length_straight_left)
    straight_left = gf.path.extrude(p1, xs_thin)
    sl = c << straight_left

    p2 = gf.path.straight(length=length_taper_wide)
    t_wide = gf.path.transition(xs_thin, xs_max, width_type='linear')
    taper_wide = gf.path.extrude_transition(p2, t_wide)
    tw = c << taper_wide
    tw.connect("o1", sl.ports["o2"])

    p3 = gf.path.straight(length=length_taper_point_left)
    t_point = gf.path.transition(xs_max, xs_point, width_type='linear')
    taper_point = gf.path.extrude_transition(p3, t_point)
    tp = c << taper_point
    tp.connect("o1", tw.ports["o2"])

    # Right part initial taper (common)
    p_in = gf.path.straight(length=l_in)
    t_in = gf.path.transition(xs_point, xs_max, width_type='linear')
    taper_in = gf.path.extrude_transition(p_in, t_in)
    ti = c << taper_in
    left_end_position = tp.ports["o2"].center
    ti.move(ti.ports["o1"], (left_end_position[0] + gap, left_end_position[1]))

    # Upper arm
    control_upper = [(0, 0), (dx_curved / 2, 0), (dx_curved / 2, dy), (dx_curved, dy)]
    p_curved_u = gf.path.bezier(control_points=control_upper)
    curved_u = gf.path.extrude(p_curved_u, xs_max)
    cu = c << curved_u
    cu.connect("o1", ti.ports["o2"])

    p_end = gf.path.straight(length=l_end)
    t_end = gf.path.transition(xs_max, xs_point, width_type='linear')
    taper_end_u = gf.path.extrude_transition(p_end, t_end)
    te_u = c << taper_end_u
    te_u.connect("o1", cu.ports["o2"])

    # Lower arm
    control_lower = [(0, 0), (dx_curved / 2, 0), (dx_curved / 2, -dy), (dx_curved, -dy)]
    p_curved_l = gf.path.bezier(control_points=control_lower)
    curved_l = gf.path.extrude(p_curved_l, xs_max)
    cl = c << curved_l
    cl.connect("o1", ti.ports["o2"])

    taper_end_l = gf.path.extrude_transition(p_end, t_end)
    te_l = c << taper_end_l
    te_l.connect("o1", cl.ports["o2"])

    return c

# Create and save
dev = device()
dev.write_gds("my_device.gds")