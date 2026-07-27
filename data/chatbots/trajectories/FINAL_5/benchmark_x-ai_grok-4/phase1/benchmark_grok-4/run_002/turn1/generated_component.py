import gdsfactory as gf
import numpy as np

def get_bezier_points(control_points, npoints=101):
    control_points = np.asanyarray(control_points)
    t = np.linspace(0, 1, npoints)
    coeffs = [
        (1 - t) ** 3,
        3 * (1 - t) ** 2 * t,
        3 * (1 - t) * t ** 2,
        t ** 3,
    ]
    points = np.sum([coeff[:, None] * control_points[i] for i, coeff in enumerate(coeffs)], axis=0)
    return points

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)
    w = 0.1
    gap = 0.05
    cc_middle = gap + w
    total_y = 0.7
    middle_y_u = cc_middle / 2
    tip_y_u = total_y / 2
    dy = tip_y_u - middle_y_u
    xs_wide = gf.cross_section.cross_section(width=w, layer=layer)
    xs_narrow = gf.cross_section.cross_section(width=1e-6, layer=layer)
    l_middle = 10.24
    dx_bend = 4.0
    total_x = 2 * dx_bend + l_middle

    # Middle straights
    straight_u = gf.components.straight(length=l_middle, cross_section=xs_wide)
    straight_upper = c << straight_u
    straight_upper.move((dx_bend, middle_y_u))

    straight_l = gf.components.straight(length=l_middle, cross_section=xs_wide)
    straight_lower = c << straight_l
    straight_lower.move((dx_bend, -middle_y_u))

    # Left upper tapered bend
    start_x = 0
    start_y = tip_y_u
    end_x = dx_bend
    end_y = middle_y_u
    control_points = [(start_x, start_y), (start_x + dx_bend / 2, start_y), (start_x + dx_bend / 2, end_y), (end_x, end_y)]
    points_lu = get_bezier_points(control_points)
    path_lu = gf.Path(points_lu)
    trans_lu = gf.path.transition(xs_narrow, xs_wide, width_type='linear')
    bend_lu = gf.path.extrude_transition(path_lu, trans_lu)
    bend_left_upper = c << bend_lu
    bend_left_upper.connect("o2", straight_upper.ports["o1"])

    # Left lower tapered bend
    start_y_l = -tip_y_u
    end_y_l = -middle_y_u
    control_points_l = [(start_x, start_y_l), (start_x + dx_bend / 2, start_y_l), (start_x + dx_bend / 2, end_y_l), (end_x, end_y_l)]
    points_ll = get_bezier_points(control_points_l)
    path_ll = gf.Path(points_ll)
    trans_ll = gf.path.transition(xs_narrow, xs_wide, width_type='linear')
    bend_ll = gf.path.extrude_transition(path_ll, trans_ll)
    bend_left_lower = c << bend_ll
    bend_left_lower.connect("o2", straight_lower.ports["o1"])

    # Right upper tapered bend
    start_x_r = dx_bend + l_middle
    start_y_r = middle_y_u
    end_x_r = total_x
    end_y_r = tip_y_u
    control_points_ru = [(start_x_r, start_y_r), (start_x_r + dx_bend / 2, start_y_r), (start_x_r + dx_bend / 2, end_y_r), (end_x_r, end_y_r)]
    points_ru = get_bezier_points(control_points_ru)
    path_ru = gf.Path(points_ru)
    trans_ru = gf.path.transition(xs_wide, xs_narrow, width_type='linear')
    bend_ru = gf.path.extrude_transition(path_ru, trans_ru)
    bend_right_upper = c << bend_ru
    bend_right_upper.connect("o1", straight_upper.ports["o2"])

    # Right lower tapered bend
    start_y_rl = -middle_y_u
    end_y_rl = -tip_y_u
    control_points_rl = [(start_x_r, start_y_rl), (start_x_r + dx_bend / 2, start_y_rl), (start_x_r + dx_bend / 2, end_y_rl), (end_x_r, end_y_rl)]
    points_rl = get_bezier_points(control_points_rl)
    path_rl = gf.Path(points_rl)
    trans_rl = gf.path.transition(xs_wide, xs_narrow, width_type='linear')
    bend_rl = gf.path.extrude_transition(path_rl, trans_rl)
    bend_right_lower = c << bend_rl
    bend_right_lower.connect("o1", straight_lower.ports["o2"])

    # Grating rungs with boolean union for the middle section
    n_rungs = 32
    p = l_middle / (n_rungs - 1)
    rung_w = p / 2
    rung_height = gap + 2 * w
    rung = gf.components.rectangle(size=(rung_w, rung_height), layer=layer, centered=True)

    # Add array of rungs
    x0 = dx_bend + rung_w / 2
    array_ref = c.add_array(rung, columns=n_rungs, rows=1, spacing=(p, 0))
    array_ref.move((x0, 0))

    return c

# Create and save
device = my_device()
device.write_gds("my_device.gds")