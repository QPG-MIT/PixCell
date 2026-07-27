import gdsfactory as gf

@gf.cell
def curved_wg(length=60.0, fanout=30.0, y_center=0.0, dy=0.0, cross_section=None):
    c = gf.Component()
    mid = c << gf.components.straight(length=length, cross_section=cross_section)
    mid.move((-length / 2, y_center))
    left = c << gf.components.bend_s(size=(fanout, dy), cross_section=cross_section)
    left.connect("o2", mid.ports["o1"])
    right = c << gf.components.bend_s(size=(fanout, -dy), cross_section=cross_section)
    right.connect("o1", mid.ports["o2"])
    return c

@gf.cell
def the_device():
    c = gf.Component()
    xs_thin = gf.cross_section.cross_section(width=0.2, layer=(1, 0))
    xs_thick = gf.cross_section.cross_section(width=1.0, layer=(1, 0))

    # Center thin
    c << curved_wg(y_center=0.0, dy=0.0, cross_section=xs_thin)

    # Bottom solid
    c << curved_wg(y_center=-1.2, dy=0.8, cross_section=xs_thick)

    # Bottom thin (3 lines)
    bottom_y = [-0.2, -0.45, -0.7]
    bottom_dy = [0.1, 0.3, 0.5]
    for y, d in zip(bottom_y, bottom_dy):
        c << curved_wg(y_center=y, dy=d, cross_section=xs_thin)

    # Top solid
    c << curved_wg(y_center=1.2, dy=-0.8, cross_section=xs_thick)

    # Top thin (3 lines)
    top_y = [0.2, 0.45, 0.7]
    top_dy = [-0.1, -0.3, -0.5]
    for y, d in zip(top_y, top_dy):
        c << curved_wg(y_center=y, dy=d, cross_section=xs_thin)

    return c

device = the_device()
device.write_gds("my_device.gds")