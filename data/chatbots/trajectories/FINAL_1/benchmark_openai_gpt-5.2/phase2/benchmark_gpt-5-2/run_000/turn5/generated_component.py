import numpy as np
import gdsfactory as gf


# Width grid needed by kfactory SymmetricalCrossSection:
# width must be a multiple of 2 dbu. With default dbu=1nm => 2nm = 0.002um.
WIDTH_GRID_UM = 0.002


def snap_w(w_um: float, grid: float = WIDTH_GRID_UM) -> float:
    """Snap width (um) to nearest multiple of `grid` (um)."""
    return round(w_um / grid) * grid


def half_cosine(s: np.ndarray) -> np.ndarray:
    """Monotonic half-cosine: f(0)=0, f(1)=1, f'(0)=f'(1)=0."""
    return 0.5 * (1 - np.cos(np.pi * s))


def taper_straight(
    length: float,
    w1: float,
    w2: float,
    layer=(1, 0),
    width_type: str = "linear",
) -> gf.Component:
    w1 = snap_w(w1)
    w2 = snap_w(w2)
    xs1 = gf.cross_section.strip(width=w1, layer=layer)
    xs2 = gf.cross_section.strip(width=w2, layer=layer)
    tr = gf.path.transition(xs1, xs2, width_type=width_type)
    p = gf.path.straight(length)
    return gf.path.extrude_transition(p, tr)


@gf.cell
def trident_splitter(
    length_total: float = 40.0,
    height_total: float = 1.7,
    layer: tuple[int, int] = (1, 0),
    # widths (ALL snapped to 0.002um internally)
    arm_w: float = 0.20,
    arm_w_in: float = 0.036,   # was 0.035 -> invalid (35nm odd)
    mid_w: float = 0.070,
    mid_w_in: float = 0.026,   # was 0.025 -> invalid (25nm odd)
    mid_w_tip: float = 0.002,  # valid (2nm)
    # vertical placement
    y0: float = 0.25,
    dy_split: float = 0.47,
    # horizontal partition (must sum to 40um)
    L_taper_in: float = 8.0,
    L_parallel: float = 19.0,
    L_curve: float = 9.0,
    L_out: float = 4.0,
    # middle prong ends earlier than curve start
    L_mid_straight: float = 8.0,
    L_mid_taper_out: float = 7.0,
    # sampling
    n_curve: int = 241,
):
    # Snap widths to satisfy kfactory (multiple of 0.002um)
    arm_w = snap_w(arm_w)
    arm_w_in = snap_w(arm_w_in)
    mid_w = snap_w(mid_w)
    mid_w_in = snap_w(mid_w_in)
    mid_w_tip = snap_w(mid_w_tip)

    if abs((L_taper_in + L_parallel + L_curve + L_out) - length_total) > 1e-9:
        raise ValueError("Require L_taper_in + L_parallel + L_curve + L_out == length_total")

    y_out = y0 + dy_split
    ymax = max(abs(y0), abs(y_out)) + arm_w / 2
    if 2 * ymax > height_total + 1e-3:
        raise ValueError(
            f"Exceeds height_total: 2*ymax={2*ymax:.3f}um > {height_total}um. "
            f"Reduce y0/dy_split/arm_w."
        )

    x_curve_start = L_taper_in + L_parallel
    x_mid_end = L_taper_in + L_mid_straight + L_mid_taper_out
    if x_mid_end > x_curve_start - 1e-6:
        raise ValueError(
            f"Middle ends too late (x_mid_end={x_mid_end:.3f}) >= curve start "
            f"(x_curve_start={x_curve_start:.3f}). Reduce L_mid_* or increase L_parallel."
        )

    c = gf.Component()
    xs_arm = gf.cross_section.strip(width=arm_w, layer=layer)

    # --- Outer arms: straight -> half-cosine offset -> straight ---
    def arm_body(dy: float) -> gf.Component:
        pts = [(0.0, 0.0), (L_parallel, 0.0)]

        s = np.linspace(0.0, 1.0, n_curve)
        f = half_cosine(s)
        xs = L_parallel + s * L_curve
        ys = dy * f

        for x, y in zip(xs[1:], ys[1:]):  # skip first to avoid duplicating (L_parallel,0)
            pts.append((float(x), float(y)))

        pts.append((L_parallel + L_curve + L_out, dy))
        p = gf.Path(pts)
        return gf.path.extrude(p, cross_section=xs_arm)

    arm_top_body = arm_body(+dy_split)
    arm_bot_body = arm_body(-dy_split)

    # --- Input tapers (linear edges like target) ---
    taper_arm_in = taper_straight(L_taper_in, arm_w_in, arm_w, layer=layer, width_type="linear")

    top_tin = c << taper_arm_in
    top_tin.move((0, y0))
    top_body = c << arm_top_body
    top_body.connect("o1", top_tin.ports["o2"])

    bot_tin = c << taper_arm_in
    bot_tin.move((0, -y0))
    bot_body = c << arm_bot_body
    bot_body.connect("o1", bot_tin.ports["o2"])

    # --- Middle: linear taper-in + straight + linear wedge-out (ends earlier) ---
    taper_mid_in = taper_straight(L_taper_in, mid_w_in, mid_w, layer=layer, width_type="linear")
    xs_mid = gf.cross_section.strip(width=mid_w, layer=layer)
    mid_st = gf.components.straight(length=L_mid_straight, cross_section=xs_mid)
    taper_mid_out = taper_straight(L_mid_taper_out, mid_w, mid_w_tip, layer=layer, width_type="linear")

    mid_in = c << taper_mid_in
    mid_s = c << mid_st
    mid_s.connect("o1", mid_in.ports["o2"])
    mid_out = c << taper_mid_out
    mid_out.connect("o1", mid_s.ports["o2"])

    # --- Ports ---
    c.add_port("in_top", port=top_tin.ports["o1"])
    c.add_port("in_mid", port=mid_in.ports["o1"])
    c.add_port("in_bot", port=bot_tin.ports["o1"])
    c.add_port("out_top", port=top_body.ports["o2"])
    c.add_port("out_bot", port=bot_body.ports["o2"])

    return c


if __name__ == "__main__":
    c = trident_splitter()
    c.show()
    c.write_gds("trident_splitter.gds")