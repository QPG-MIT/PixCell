import gdsfactory as gf

@gf.cell
def arm(l1: float, l2: float, w_narrow: float, w_wide: float, layer: tuple):
    arm_c = gf.Component()

    xs_narrow = gf.cross_section.cross_section(width=w_narrow, layer=layer)
    xs_wide = gf.cross_section.cross_section(width=w_wide, layer=layer)

    trans1 = gf.path.transition(xs_narrow, xs_wide, width_type='sine')
    p1 = gf.path.straight(length=l1)
    part1 = gf.path.extrude_transition(p1, trans1)

    trans2 = gf.path.transition(xs_wide, xs_narrow, width_type='sine')
    p2 = gf.path.straight(length=l2)
    part2 = gf.path.extrude_transition(p2, trans2)

    p1_ref = arm_c << part1
    p2_ref = arm_c << part2
    p2_ref.connect("o1", p1_ref.ports["o2"])

    return arm_c

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)

    half = 4.7 / 2
    w_narrow = 0.1
    w_wide = 1.2
    l1 = 1.5
    l2 = half - l1

    base_arm = arm(l1, l2, w_narrow, w_wide, layer)

    # Right arm (no rotation)
    arm_r = gf.Component("arm_right")
    ref_r = arm_r << base_arm

    # Left arm
    arm_l = gf.Component("arm_left")
    ref_l = arm_l << base_arm
    ref_l.rotate(180, center=(0, 0))

    # Up arm
    arm_u = gf.Component("arm_up")
    ref_u = arm_u << base_arm
    ref_u.rotate(90, center=(0, 0))

    # Down arm
    arm_d = gf.Component("arm_down")
    ref_d = arm_d << base_arm
    ref_d.rotate(-90, center=(0, 0))

    # Boolean unions
    u = gf.boolean(arm_r, arm_l, "or", layer=layer)
    u = gf.boolean(u, arm_u, "or", layer=layer)
    u = gf.boolean(u, arm_d, "or", layer=layer)

    c << u

    return c

device = my_device()
device.write_gds("my_device.gds")