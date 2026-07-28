import gdsfactory as gf


# Top-level, JEE-substitutable geometry knobs (micrometres).
wg_width = 0.236
lobe_width = 0.91
lobe_half_length = 1.80
port_length = 0.55
taper_length = 0.45

layer = (1, 0)


@gf.cell
def cardinal_arm():
    """One +x arm, centered on y=0, from the junction to its port."""
    c = gf.Component()
    # Four short tapers approximate the smooth convex lens edge while
    # remaining within the primitive-only catalog.
    widths = [wg_width, 0.75, lobe_width, 0.75, wg_width]
    for i, (w1, w2) in enumerate(zip(widths[:-1], widths[1:])):
        t = c << gf.components.taper(
            length=taper_length,
            width1=w1,
            width2=w2,
            layer=layer,
        )
        t.move((i * taper_length, 0))
    p = c << gf.components.straight(
        length=port_length,
        cross_section=gf.cross_section.strip(width=wg_width, layer=layer),
    )
    p.move((lobe_half_length, 0))
    return c


@gf.cell
def device():
    c = gf.Component()
    arm = cardinal_arm()
    for angle in (0, 90, 180, 270):
        ref = c << arm
        ref.rotate(angle, center=(0, 0))
    return c


if __name__ == "__main__":
    component = device()
    component.write_gds("device.gds")
