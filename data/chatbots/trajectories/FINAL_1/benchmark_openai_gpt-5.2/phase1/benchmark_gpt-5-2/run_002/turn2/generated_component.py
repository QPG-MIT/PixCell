import gdsfactory as gf


@gf.cell
def three_to_two_fanout_v2(
    footprint_um: tuple[float, float] = (40.0, 1.7),
    layer: tuple[int, int] = (1, 0),
    wg_width: float = 0.18,
    gap_in: float = 0.18,          # visible white gap between parallel inputs
    l_straight1: float = 24.0,     # left straight (before S-bends)
    l_sbend: float = 10.0,         # S-bend x-length
    l_straight2: float = 6.0,      # right straight (after S-bends)
    l_mid_straight: float = 25.0,  # middle runs a bit longer than bend start in the picture
    l_mid_taper: float = 3.0,
    mid_width2: float = 0.03,      # very thin tip to look like it "ends"
) -> gf.Component:
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)

    Lx, Ly = footprint_um

    # Make outputs sit close to the top/bottom of the allowed height.
    y_out = Ly / 2 - wg_width / 2

    # Input pitch chosen to prevent merging on the left.
    pitch_in = wg_width + gap_in
    y_in = pitch_in

    # Ensure total X length matches footprint (parametric, not hardcoded polygon)
    total_length = l_straight1 + l_sbend + l_straight2
    if abs(total_length - Lx) > 1e-6:
        raise ValueError(f"Set lengths to sum to footprint X: {total_length=} vs {Lx=}")

    # --- TOP arm ---
    r1t = c << gf.components.straight(length=l_straight1, cross_section=xs)
    r1t.move((0, y_in))

    rbt = c << gf.components.bend_s(size=(l_sbend, y_out - y_in), cross_section=xs)
    rbt.connect("o1", r1t.ports["o2"])

    r2t = c << gf.components.straight(length=l_straight2, cross_section=xs)
    r2t.connect("o1", rbt.ports["o2"])

    # --- BOTTOM arm ---
    r1b = c << gf.components.straight(length=l_straight1, cross_section=xs)
    r1b.move((0, -y_in))

    rbb = c << gf.components.bend_s(size=(l_sbend, -(y_out - y_in)), cross_section=xs)
    rbb.connect("o1", r1b.ports["o2"])

    r2b = c << gf.components.straight(length=l_straight2, cross_section=xs)
    r2b.connect("o1", rbb.ports["o2"])

    # --- MIDDLE arm (ends before the split region with a taper-to-tip) ---
    rmid_s = c << gf.components.straight(length=l_mid_straight, cross_section=xs)
    rmid_s.move((0, 0))

    rmid_t = c << gf.components.taper(
        length=l_mid_taper, width1=wg_width, width2=mid_width2, layer=layer
    )
    rmid_t.connect("o1", rmid_s.ports["o2"])

    # Ports
    c.add_port("in_top", port=r1t.ports["o1"])
    c.add_port("in_mid", port=rmid_s.ports["o1"])
    c.add_port("in_bot", port=r1b.ports["o1"])
    c.add_port("out_top", port=r2t.ports["o2"])
    c.add_port("out_bot", port=r2b.ports["o2"])

    return c


if __name__ == "__main__":
    c = three_to_two_fanout_v2()
    c.write_gds("three_to_two_fanout_v2.gds")