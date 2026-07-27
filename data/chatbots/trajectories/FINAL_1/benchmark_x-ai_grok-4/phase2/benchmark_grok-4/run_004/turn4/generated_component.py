import gdsfactory as gf
import math

@gf.cell
def make_diamond(length, max_width, layer, min_width=0.002, width_type='linear'):
    p1 = gf.path.straight(length=length/2)
    p2 = gf.path.straight(length=length/2)
    xs1 = gf.cross_section.cross_section(width=min_width, layer=layer)
    xs2 = gf.cross_section.cross_section(width=max_width, layer=layer)
    trans1 = gf.path.transition(xs1, xs2, width_type=width_type)
    trans2 = gf.path.transition(xs2, xs1, width_type=width_type)
    t1 = gf.path.extrude_transition(p1, trans1)
    t2 = gf.path.extrude_transition(p2, trans2)
    d = gf.Component()
    r1 = d << t1
    r2 = d << t2
    r2.connect("o1", r1.ports["o2"])
    return d

@gf.cell
def make_arm(dy, dx, max_width, layer, min_width=0.002):
    final_dy = math.copysign(0.85, dy)
    theta = math.atan2(final_dy, dx)
    length_total = dx / math.cos(theta)
    l1 = 4.0
    l2 = length_total - l1
    cos_th = math.cos(theta)
    sin_th = math.sin(theta)
    end1_x = l1 * cos_th
    end1_y = l1 * sin_th
    end2_x = (l1 + l2) * cos_th
    end2_y = (l1 + l2) * sin_th
    xs1 = gf.cross_section.cross_section(width=min_width, layer=layer)
    xs2 = gf.cross_section.cross_section(width=max_width, layer=layer)
    trans1 = gf.path.transition(xs1, xs2, width_type='linear')
    trans2 = gf.path.transition(xs2, xs1, width_type='linear')
    p1 = gf.Path([(0.0, 0.0), (end1_x, end1_y)])
    t1 = gf.path.extrude_transition(p1, trans1)
    p2 = gf.Path([(end1_x, end1_y), (end2_x, end2_y)])
    t2 = gf.path.extrude_transition(p2, trans2)
    a = gf.Component()
    a << t1
    a << t2
    return a

@gf.cell
def device():
    c = gf.Component()
    layer = (1, 0)
    gap = 0.0
    d1_length = 4.0
    d1_width = 0.5
    d2_length = 10.0
    d2_width = 0.6
    right_dx = 25.6
    right_dy = 0.55
    right_width = 0.6
    min_width = 0.002
    d1 = c << make_diamond(d1_length, d1_width, layer, min_width)
    d1.move((0, 0))
    d2 = c << make_diamond(d2_length, d2_width, layer, min_width)
    d2.move((d1.xmax + gap, 0))
    upper_arm = c << make_arm(right_dy, right_dx, right_width, layer, min_width)
    lower_arm = c << make_arm(-right_dy, right_dx, right_width, layer, min_width)
    right_start_x = d2.xmax + gap
    upper_arm.move((right_start_x, 0))
    lower_arm.move((right_start_x, 0))
    return c

dev = device()
dev.write_gds("my_device.gds")