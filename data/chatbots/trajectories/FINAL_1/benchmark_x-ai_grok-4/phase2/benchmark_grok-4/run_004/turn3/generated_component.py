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
    curve_dx = 4.0
    taper_length = dx - curve_dx
    points = [(0, 0), (2, dy), (4, dy)]
    p = gf.path.smooth(points, radius=1.0)
    xs1 = gf.cross_section.cross_section(width=min_width, layer=layer)
    xs2 = gf.cross_section.cross_section(width=max_width, layer=layer)
    trans = gf.path.transition(xs1, xs2, width_type='linear')
    curved = gf.path.extrude_transition(p, trans)
    # Taper with slight arc
    additional_dy = math.copysign(max_width / 2, dy)
    r = (taper_length ** 2) / (2 * abs(additional_dy))
    alpha = taper_length / r
    angle = math.degrees(alpha) * (1 if dy > 0 else -1)
    p2 = gf.path.arc(radius=r, angle=angle)
    trans2 = gf.path.transition(xs2, xs1, width_type='linear')
    end_taper = gf.path.extrude_transition(p2, trans2)
    a = gf.Component()
    r_curved = a << curved
    r_taper = a << end_taper
    r_taper.connect("o1", r_curved.ports["o2"])
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