import gdsfactory as gf

@gf.cell
def arm(length: float, w_narrow: float, w_wide: float, layer: tuple):
    arm_c = gf.Component()

    xs_narrow = gf.cross_section.cross_section(width=w_narrow, layer=layer)
    xs_wide = gf.cross_section.cross_section(width=w_wide, layer=layer)

    trans = gf.path.transition(xs_wide, xs_narrow, width_type='sine')
    p = gf.path.straight(length=length)
    part = gf.path.extrude_transition(p, trans)

    part_ref = arm_c << part

    # Add tip circle for rounding
    radius_tip = w_narrow / 2
    tip = gf.components.circle(radius=radius_tip, layer=layer)
    tip_ref = arm_c << tip
    tip_ref.move(origin=(0, 0), destination=(length - radius_tip, 0))

    return arm_c

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)

    half = 4.7 / 2
    w_narrow = 0.2
    w_wide = 1.5
    length = half

    base_arm = arm(length, w_narrow, w_wide, layer)

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