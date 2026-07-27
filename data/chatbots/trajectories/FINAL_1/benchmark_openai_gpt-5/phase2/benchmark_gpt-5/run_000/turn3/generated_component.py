import gdsfactory as gf

LAYER = (1, 0)
FOOTPRINT_X = 40.0
FOOTPRINT_Y = 1.7


@gf.cell
def right_body(
    w=0.70,        # boundary width
    gap=0.12,      # slit opening at the left
    dx=10.0,       # S-bend length
    dy=0.44,       # vertical offset so total height = 1.7 um
    W=15.0,        # width of the solid block on the right
    overlap=0.6,   # rectangle overlaps S-bends to avoid the inner pocket
) -> gf.Component:
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=w, layer=LAYER)

    # Two S-bends that create the nozzle throat
    s_top = c << gf.components.bend_s(size=(dx, +dy), cross_section=xs)
    s_top.movey(+gap / 2)
    s_bot = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    s_bot.movey(-gap / 2)

    # Total height fixed to 1.7 µm
    H = 2 * (w / 2 + dy) + gap

    # Rectangle starts a bit to the left of S-bend end to guarantee overlap
    rect = c << gf.components.rectangle(size=(W + overlap, H), layer=LAYER, centered=False)
    rect.move((dx - overlap, -H / 2))

    # Union (no precision kwarg)
    u = gf.boolean(s_top, rect, operation="or", layer=LAYER)
    body = gf.boolean(u, s_bot, operation="or", layer=LAYER)
    return body


@gf.cell
def three_tapers(length=14.5, pitch=0.56, w1=0.45, w2=0.06) -> gf.Component:
    c = gf.Component()
    t_mid = c << gf.components.taper(length=length, width1=w1, width2=w2, layer=LAYER)
    t_top = c << gf.components.taper(length=length, width1=w1, width2=w2, layer=LAYER)
    t_bot = c << gf.components.taper(length=length, width1=w1, width2=w2, layer=LAYER)
    t_top.movey(+pitch)
    t_bot.movey(-pitch)
    return c


@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    # Build right side first to compute placement
    w = 0.70
    gap = 0.12
    dx = 10.0
    dy = 0.44
    W = 15.0
    overlap = 0.6
    right = c << right_body(w=w, gap=gap, dx=dx, dy=dy, W=W, overlap=overlap)

    # X-span of the right body
    right_span = (dx - overlap) + W

    # Place it so the overall device width is ~40 µm
    offset_right = FOOTPRINT_X - right_span
    right.movex(offset_right)

    # Left tapers: stop just before the nozzle to keep a small gap
    gap_to_nozzle = 0.7
    taper_length = max(5.0, offset_right - gap_to_nozzle)
    left = c << three_tapers(length=taper_length)
    left.move((0, 0))

    return c


if __name__ == "__main__":
    D = device()
    D.write_gds("recreated_device_iter3.gds")
    print("Wrote GDS: recreated_device_iter3.gds")