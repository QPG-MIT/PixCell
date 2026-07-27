# Improved geometry: three clearly separated tapers on the left and two wide rails on the right.
# Builds only from parametric primitives and saves a GDS.

import gdsfactory as gf


@gf.cell
def fork_with_triple_tapers():
    c = gf.Component()

    W = 40.0   # footprint length
    H = 1.7    # footprint height (not used directly, just a guide)

    # Left tapered fingers
    L_taper = 22.0
    gap_x = 0.30          # small horizontal gap to the right rails
    s_dx = 8.0            # S-bend horizontal span
    L_right = W - (L_taper + gap_x + s_dx)

    # Left widths: choose centers so tapers do not overlap
    w_mid1 = 0.80
    w_top1 = 0.44
    w_bot1 = 0.44
    G = 0.08  # vertical gap between tapers (at the fat side)

    y_top = (w_mid1 / 2) + G + (w_top1 / 2)   # ~0.70
    y_bot = -y_top

    # Make the three tapers
    t_mid = c << gf.components.taper(length=L_taper, width1=w_mid1, width2=0.12, cross_section="strip")
    t_top = c << gf.components.taper(length=L_taper, width1=w_top1, width2=0.06, cross_section="strip")
    t_bot = c << gf.components.taper(length=L_taper, width1=w_bot1, width2=0.06, cross_section="strip")

    t_mid.move((0, 0))
    t_top.move((0, y_top))
    t_bot.move((0, y_bot))

    # Right-side two thick rails with smooth inward curvature
    xs_wide = gf.cross_section.strip(width=0.60, layer=(1, 0))
    y_start = 0.55  # places outer edges close to ±0.85 (half of 1.7)

    s_top = c << gf.components.bend_s(size=(s_dx, -0.25), cross_section=xs_wide)
    s_bot = c << gf.components.bend_s(size=(s_dx, +0.25), cross_section=xs_wide)

    # Place S-bends by aligning their input-port centers
    p = s_top.ports["o1"]
    s_top.move(((L_taper + gap_x) - p.center[0], y_start - p.center[1]))
    p = s_bot.ports["o1"]
    s_bot.move(((L_taper + gap_x) - p.center[0], -y_start - p.center[1]))

    # Straight rails extending to the right boundary
    st_top = c << gf.components.straight(length=L_right, cross_section=xs_wide)
    st_bot = c << gf.components.straight(length=L_right, cross_section=xs_wide)
    st_top.connect("o1", s_top.ports["o2"])
    st_bot.connect("o1", s_bot.ports["o2"])

    return c


if __name__ == "__main__":
    comp = fork_with_triple_tapers()
    comp.write_gds("fork_with_triple_tapers.gds")
    print("Wrote GDS: fork_with_triple_tapers.gds")