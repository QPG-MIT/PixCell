import gdsfactory as gf


@gf.cell
def _branch_straight_then_offset(
    length: float,
    l_straight: float,
    dy: float,
    cross_section,
):
    """Straight section followed by a smooth offset (bend_s)."""
    if l_straight >= length:
        raise ValueError("l_straight must be smaller than length.")

    dx = length - l_straight

    c = gf.Component()

    s = c << gf.components.straight(length=l_straight, cross_section=cross_section)
    b = c << gf.components.bend_s(size=(dx, dy), cross_section=cross_section)
    b.connect("o1", s.ports["o2"])

    c.add_port("o1", port=s.ports["o1"])
    c.add_port("o2", port=b.ports["o2"])
    return c


@gf.cell
def three_to_two_adiabatic_like(
    length: float = 40.0,
    height: float = 1.7,
    wg_width: float = 0.5,
    layer: tuple[int, int] = (1, 0),
    y_in: float = 0.30,        # input outer guides at +/- y_in, center at 0
    l_straight: float = 26.0,  # long straight before the gentle split
    l_center: float = 28.0,    # center guide ends early (stub)
):
    """
    Recreates the shown geometry using only parametric primitives:
    - Top/bottom: straight + smooth offset (bend_s)
    - Middle: straight stub ending early

    Footprint target: (length x height) = 40.0 x 1.7 um
    """
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)

    # Enforce the overall vertical footprint:
    # total height = 2*(y_out + wg_width/2) = height  -> y_out = height/2 - wg_width/2
    y_out = (height / 2) - (wg_width / 2)

    # Top and bottom branches (3 inputs -> 2 outputs)
    top_branch = _branch_straight_then_offset(
        length=length, l_straight=l_straight, dy=(y_out - y_in), cross_section=xs
    )
    bot_branch = _branch_straight_then_offset(
        length=length, l_straight=l_straight, dy=(-(y_out) - (-(y_in))), cross_section=xs
    )

    top = c << top_branch
    top.move((0, y_in))

    bot = c << bot_branch
    bot.move((0, -y_in))

    # Middle stub (ends early)
    mid = c << gf.components.straight(length=l_center, cross_section=xs)
    mid.move((0, 0))

    # Expose ports (3 on left, 2 on right)
    c.add_port("o1_top_in", port=top.ports["o1"])
    c.add_port("o2_mid_in", port=mid.ports["o1"])
    c.add_port("o3_bot_in", port=bot.ports["o1"])
    c.add_port("o4_top_out", port=top.ports["o2"])
    c.add_port("o5_bot_out", port=bot.ports["o2"])

    return c


if __name__ == "__main__":
    d = three_to_two_adiabatic_like()
    d.show()
    d.write_gds("recreated_device.gds")