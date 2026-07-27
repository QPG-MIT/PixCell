import gdsfactory as gf

@gf.cell
def my_device():
    r = 1.0
    w = 1.0
    L = 3.5
    gap_width = 0.5
    gap_height = w * 1.2

    xs = gf.cross_section.cross_section(width=w, layer=(1, 0), radius_min=0.5)

    c = gf.Component()

    # Bottom straight
    bottom = c << gf.components.straight(length=L, cross_section=xs)
    bottom.move((-L / 2, -r))

    # Top straight
    top = c << gf.components.straight(length=L, cross_section=xs)
    top.move((-L / 2, r))

    # Right bend
    bend_right = c << gf.components.bend_circular(radius=r, angle=180, cross_section=xs)
    bend_right.connect("o1", bottom.ports["o2"])

    # Left bend
    bend_left = c << gf.components.bend_circular(radius=r, angle=180, cross_section=xs)
    bend_left.mirror(p1=(0, 0), p2=(0, 1))
    bend_left.connect("o1", bottom.ports["o1"])

    # Gaps
    gaps = gf.Component()
    gap_top = gaps << gf.components.rectangle(size=(gap_width, gap_height), layer=(1, 0), centered=True)
    gap_top.move((0, r))
    gap_bottom = gaps << gf.components.rectangle(size=(gap_width, gap_height), layer=(1, 0), centered=True)
    gap_bottom.move((0, -r))

    # Flatten to merge polygons before boolean
    c.flatten()

    # Boolean subtract
    device = gf.boolean(c, gaps, operation="not", layer=(1, 0))

    return device

device = my_device()
device.write_gds("my_device.gds")