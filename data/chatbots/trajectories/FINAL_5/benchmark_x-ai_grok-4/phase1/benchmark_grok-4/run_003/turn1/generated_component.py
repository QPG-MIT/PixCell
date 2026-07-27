import gdsfactory as gf

@gf.cell
def grating_coupler(
    length: float = 8.0,
    gap: float = 0.1,
    width: float = 0.2,
    n_bars: int = 10,
    bar_width: float = 0.2,
    bar_height: float = 0.2,
    layer: tuple[int, int] = (1, 0),
) -> gf.Component:
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=width, layer=layer)
    s = gf.components.straight(length=length, cross_section=xs)
    upper = c << s
    lower = c << s
    center_spacing = gap / 2 + width / 2
    upper.movey(center_spacing)
    lower.movey(-center_spacing)
    step = length / n_bars
    for i in range(n_bars):
        bar = gf.components.rectangle(size=(bar_width, bar_height), layer=layer, centered=True)
        b = c << bar
        b.movex((i + 0.5) * step)
    c.add_port("upper_o1", port=upper.ports["o1"])
    c.add_port("upper_o2", port=upper.ports["o2"])
    c.add_port("lower_o1", port=lower.ports["o1"])
    c.add_port("lower_o2", port=lower.ports["o2"])
    return c

@gf.cell
def my_device() -> gf.Component:
    c = gf.Component()
    layer = (1, 0)
    width = 0.2
    gap = 0.1
    dy_bend = 0.1
    center_spacing = gap / 2 + width / 2  # 0.15
    end_spacing = center_spacing + dy_bend  # 0.25
    middle_length = 8.0
    total_length = 18.24
    side_length = (total_length - middle_length) / 2  # 5.12
    taper_length = 2.0
    bend_length = side_length - taper_length  # 3.12
    xs = gf.cross_section.cross_section(width=width, layer=layer)

    # Left tapers
    taper_left = gf.components.taper(
        length=taper_length, width1=0.002, width2=width, layer=layer
    )
    tlu = c << taper_left
    tlu.move((0, end_spacing))
    tll = c << taper_left
    tll.move((0, -end_spacing))

    # Left bends
    bend_left_upper = gf.components.bend_s(
        size=(bend_length, -dy_bend), cross_section=xs
    )
    blu = c << bend_left_upper
    blu.connect("o1", tlu.ports["o2"])

    bend_left_lower = gf.components.bend_s(
        size=(bend_length, dy_bend), cross_section=xs
    )
    bll = c << bend_left_lower
    bll.connect("o1", tll.ports["o2"])

    # Middle grating coupler
    middle = c << grating_coupler(
        length=middle_length,
        gap=gap,
        width=width,
        n_bars=10,
        bar_width=0.2,
        bar_height=0.2,
        layer=layer,
    )
    middle.connect("upper_o1", blu.ports["o2"])

    # Right bends
    bend_right_upper = gf.components.bend_s(
        size=(bend_length, dy_bend), cross_section=xs
    )
    bru = c << bend_right_upper
    bru.connect("o1", middle.ports["upper_o2"])

    bend_right_lower = gf.components.bend_s(
        size=(bend_length, -dy_bend), cross_section=xs
    )
    brl = c << bend_right_lower
    brl.connect("o1", middle.ports["lower_o2"])

    # Right tapers
    taper_right = gf.components.taper(
        length=taper_length, width1=width, width2=0.002, layer=layer
    )
    tru = c << taper_right
    tru.connect("o1", bru.ports["o2"])

    trl = c << taper_right
    trl.connect("o1", brl.ports["o2"])

    return c

device = my_device()
device.write_gds("my_device.gds")