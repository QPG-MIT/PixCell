import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    w = 0.5
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))

    # Parameters
    length = 80
    gap = 0.2
    dx = 20
    sep_ends = 4 - w  # To match 4um height bounding box
    dy_upper_left = (gap + w) / 2 - sep_ends / 2
    dy_lower_left = - (gap + w) / 2 + sep_ends / 2
    dy_upper_right = sep_ends / 2 - (gap + w) / 2
    dy_lower_right = - sep_ends / 2 + (gap + w) / 2

    # Central coupler
    coupler = gf.components.coupler_straight(length=length, gap=gap, cross_section=xs)
    coup = c << coupler

    # Left upper bend
    bend_ul = gf.components.bend_s(size=(dx, dy_upper_left), cross_section=xs)
    bul = c << bend_ul
    bul.connect("o2", coup.ports["o1"])

    # Left lower bend
    bend_ll = gf.components.bend_s(size=(dx, dy_lower_left), cross_section=xs)
    bll = c << bend_ll
    bll.connect("o2", coup.ports["o3"])

    # Right upper bend
    bend_ur = gf.components.bend_s(size=(dx, dy_upper_right), cross_section=xs)
    bur = c << bend_ur
    bur.connect("o1", coup.ports["o2"])

    # Right lower bend
    bend_lr = gf.components.bend_s(size=(dx, dy_lower_right), cross_section=xs)
    blr = c << bend_lr
    blr.connect("o1", coup.ports["o4"])

    # Expose external ports
    c.add_port("o1", port=bul.ports["o1"])
    c.add_port("o2", port=bur.ports["o2"])
    c.add_port("o3", port=bll.ports["o1"])
    c.add_port("o4", port=blr.ports["o2"])

    return c

# Create and save
device = my_device()
device.write_gds("my_device.gds")