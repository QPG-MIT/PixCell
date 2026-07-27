# Recreated geometry that matches the provided image and footprint
# Uses only parametric primitives (no raw polygons) and writes a GDS file.

import gdsfactory as gf


@gf.cell
def fork_body() -> gf.Component:
    """Right-side fork: a neck taper that splits into two branches."""
    c = gf.Component()

    # Neck that broadens into the fork (match width with the S-bends)
    w_fork = 0.70
    neck = c << gf.components.taper(length=3.0, width1=0.18, width2=w_fork, layer=(1, 0))

    xs_fork = gf.cross_section.cross_section(width=w_fork, layer=(1, 0))

    # Two symmetric S-bends and straight outputs
    dy = 0.35
    dx = 8.0

    s_top = c << gf.components.bend_s(size=(dx, dy), cross_section=xs_fork)
    s_top.connect("o1", neck.ports["o2"])

    s_bot = c << gf.components.bend_s(size=(dx, dy), cross_section=xs_fork)
    s_bot.mirror(p1=(0, 0), p2=(1, 0))
    s_bot.connect("o1", neck.ports["o2"])

    st_top = c << gf.components.straight(length=6.0, cross_section=xs_fork)
    st_bot = c << gf.components.straight(length=6.0, cross_section=xs_fork)
    st_top.connect("o1", s_top.ports["o2"])
    st_bot.connect("o1", s_bot.ports["o2"])

    return c


@gf.cell
def three_tapers() -> gf.Component:
    """Left three tapered strips that approach the fork."""
    c = gf.Component()

    L = 18.0
    w_wide = 0.45
    w_tip = 0.06

    t_center = c << gf.components.taper(length=L, width1=w_wide, width2=w_tip, layer=(1, 0))
    t_top = c << gf.components.taper(length=L, width1=w_wide, width2=w_tip, layer=(1, 0))
    t_bot = c << gf.components.taper(length=L, width1=w_wide, width2=w_tip, layer=(1, 0))

    # Vertical placement (keeps total height within ~1.7 um)
    t_top.movey(+0.50)
    t_bot.movey(-0.50)

    return c


@gf.cell
def device() -> gf.Component:
    """Full device within ~40 x 1.7 um footprint."""
    c = gf.Component()
    taps = c << three_tapers()
    taps.move((0, 0))

    fork = c << fork_body()
    # Position the fork to obtain ~40 µm overall length
    fork.movex(21.0)

    return c


if __name__ == "__main__":
    D = device()
    D.write_gds("recreated_device.gds")
    print("Wrote GDS: recreated_device.gds")