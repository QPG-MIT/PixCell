import gdsfactory as gf

LAYER = (1, 0)


@gf.cell
def taper_transition(
    length: float = 8.0,
    width1: float = 0.12,
    width2: float = 0.26,
    layer=LAYER,
    width_type: str = "sine",
) -> gf.Component:
    """Parametric taper using Path + extrude_transition."""
    xs1 = gf.cross_section.strip(width=width1, layer=layer)
    xs2 = gf.cross_section.strip(width=width2, layer=layer)
    trans = gf.path.transition(xs1, xs2, width_type=width_type)
    p = gf.path.straight(length=length)
    return gf.path.extrude_transition(p, trans)


@gf.cell
def three_waveguides_split_like_png(
    # Footprint target
    length_total: float = 40.0,
    height_total: float = 1.7,
    layer=LAYER,
    # Geometry tuned to avoid left-side merging and match the visual proportions
    w_wg: float = 0.26,
    w_start: float = 0.12,
    ltaper: float = 8.0,
    lcpl: float = 18.0,          # straight "parallel" region length after taper
    lfan_dx: float = 8.0,        # horizontal length of the fan-out
    smooth_radius: float = 6.0,  # smoothing radius for the fan-out
    y_cpl: float = 0.48,         # outer guides y in parallel region
    y_out: float = 0.72,         # outer guides y at outputs
    center_end_offset: float = 1.0,  # center guide ends before fan-out starts
) -> gf.Component:
    """
    Matches the original intent:
    - 3 separate thin waveguides (no wide merged trunk).
    - Middle guide terminates before the outer fan-out.
    - Outer guides smoothly S-bend outward.
    """
    c = gf.Component()
    xs = gf.cross_section.strip(width=w_wg, layer=layer)

    # Sanity check (keep within height_total)
    half_h = height_total / 2
    if abs(y_out) + w_wg / 2 > half_h + 1e-6:
        raise ValueError("y_out/w_wg exceed the requested 1.7um height footprint.")

    dy_fan = y_out - y_cpl
    rest_len = length_total - ltaper
    # rest_len should equal lcpl + lfan_dx + lout
    lout = rest_len - (lcpl + lfan_dx)
    if lout <= 0:
        raise ValueError("Lengths invalid: need length_total > ltaper + lcpl + lfan_dx.")

    # -------------------------
    # Outer TOP waveguide
    # -------------------------
    top_taper = c << taper_transition(length=ltaper, width1=w_start, width2=w_wg, layer=layer)
    top_taper.move((0, y_cpl))

    # Smooth fan-out path (constant width), starting at taper end
    p_top = gf.path.smooth(
        points=[
            (0, 0),
            (lcpl, 0),
            (lcpl + lfan_dx, dy_fan),
            (lcpl + lfan_dx + lout, dy_fan),
        ],
        radius=smooth_radius,
    )
    top_rest = c << gf.path.extrude(p_top, cross_section=xs)
    top_rest.connect("o1", top_taper.ports["o2"])

    # -------------------------
    # Outer BOTTOM waveguide
    # -------------------------
    bot_taper = c << taper_transition(length=ltaper, width1=w_start, width2=w_wg, layer=layer)
    bot_taper.move((0, -y_cpl))

    p_bot = gf.path.smooth(
        points=[
            (0, 0),
            (lcpl, 0),
            (lcpl + lfan_dx, -dy_fan),
            (lcpl + lfan_dx + lout, -dy_fan),
        ],
        radius=smooth_radius,
    )
    bot_rest = c << gf.path.extrude(p_bot, cross_section=xs)
    bot_rest.connect("o1", bot_taper.ports["o2"])

    # -------------------------
    # Center waveguide (ends early)
    # -------------------------
    # End just before fan-out begins (fan-out begins at x = ltaper + lcpl)
    x_end_center = ltaper + lcpl - center_end_offset
    if x_end_center <= ltaper:
        raise ValueError("center_end_offset too large; center would be negative length.")

    mid_taper = c << taper_transition(length=ltaper, width1=w_start, width2=w_wg, layer=layer)
    mid_taper.move((0, 0))

    mid_straight = c << gf.components.straight(length=x_end_center - ltaper, cross_section=xs)
    mid_straight.connect("o1", mid_taper.ports["o2"])

    # Ports
    c.add_port("o1", port=mid_taper.ports["o1"])      # center input
    c.add_port("o2", port=top_rest.ports["o2"])       # top output
    c.add_port("o3", port=bot_rest.ports["o2"])       # bottom output

    return c


if __name__ == "__main__":
    c = three_waveguides_split_like_png()
    c.write_gds("recreated_device_v2.gds")