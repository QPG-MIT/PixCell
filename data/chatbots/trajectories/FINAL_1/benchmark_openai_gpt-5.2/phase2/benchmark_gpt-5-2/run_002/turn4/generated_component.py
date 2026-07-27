import numpy as np
import gdsfactory as gf


def _smoothstep5(u: np.ndarray) -> np.ndarray:
    """Quintic smoothstep: C2 at endpoints (0..1)."""
    return 10 * u**3 - 15 * u**4 + 6 * u**5


def _warp_symmetric(t: np.ndarray, k: float) -> np.ndarray:
    """
    Symmetric time-warp around 0.5.
    k=1 -> identity
    k>1 -> slower near ends, faster mid (bend starts later/ends earlier visually)
    """
    if k <= 1.0:
        return t

    tw = np.empty_like(t)
    left = t <= 0.5
    # map [0, 0.5] -> [0, 0.5] with power k
    tw[left] = 0.5 * (2.0 * t[left]) ** k
    # map [0.5, 1] -> [0.5, 1] symmetrically
    tw[~left] = 1.0 - 0.5 * (2.0 * (1.0 - t[~left])) ** k
    return tw


def _sbend_quintic_points(
    dx: float,
    dy: float,
    n: int = 301,
    warp: float = 1.6,
) -> list[tuple[float, float]]:
    """
    Point-sampled S-bend from (0,0) to (dx,dy) with:
    - y'(0)=y'(1)=0 (horizontal tangents)
    - y''(0)=y''(1)=0 (zero curvature at joins)  -> removes the 'kink' you see
    """
    t = np.linspace(0.0, 1.0, n)
    tw = _warp_symmetric(t, warp)
    s = _smoothstep5(tw)
    x = dx * t
    y = dy * s
    return list(zip(x.tolist(), y.tolist()))


@gf.cell
def three_to_two_fanout_v4(
    footprint_um: tuple[float, float] = (40.0, 1.7),
    layer: tuple[int, int] = (1, 0),
    wg_width: float = 0.18,
    gap_in: float = 0.18,
    # X partition (must sum to footprint_um[0])
    l_pre: float = 22.0,
    l_curve: float = 16.0,
    l_post: float = 2.0,
    # Fanout shape control
    bend_warp: float = 1.7,      # >1 pushes bend "later" (closer to target look)
    bend_npoints: int = 401,     # more points = smoother raster/less faceting
    # Middle arm "wedge"
    l_mid_taper: float = 7.0,    # longer wedge to resemble target
    mid_width2: float = 0.03,
    mid_end_offset: float = 0.35,  # tip ends slightly before bend start
    # Vertical placement
    y_out_margin: float | None = None,
) -> gf.Component:
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)

    Lx, Ly = footprint_um
    total_x = l_pre + l_curve + l_post
    if abs(total_x - Lx) > 1e-6:
        raise ValueError(f"Set l_pre+l_curve+l_post to Lx. Got {total_x=} vs {Lx=}")

    if y_out_margin is None:
        y_out_margin = wg_width / 2

    # Output centerlines close to top/bottom of footprint
    y_out = Ly / 2 - y_out_margin

    # Input centerline spacing (3 inputs on the left)
    pitch_in = wg_width + gap_in
    y_in = pitch_in

    dy = y_out - y_in
    if dy <= 0:
        raise ValueError(
            f"Need y_out > y_in. Got {y_out=} <= {y_in=}. "
            f"Increase Ly, reduce gap_in, or reduce y_out_margin."
        )

    def fanout_path(dy_local: float) -> gf.Path:
        # C2-continuous S-bend section
        sb_pts = _sbend_quintic_points(
            dx=l_curve,
            dy=dy_local,
            n=bend_npoints,
            warp=bend_warp,
        )
        p_sb = gf.Path(sb_pts)
        return gf.path.straight(l_pre) + p_sb + gf.path.straight(l_post)

    # TOP arm
    top = gf.path.extrude(fanout_path(+dy), cross_section=xs)
    rt = c << top
    rt.move((0, y_in))

    # BOTTOM arm
    bot = gf.path.extrude(fanout_path(-dy), cross_section=xs)
    rb = c << bot
    rb.move((0, -y_in))

    # MIDDLE arm: straight then long taper to a thin tip, ending before bend start
    x_bend_start = l_pre
    x_mid_tip = x_bend_start - mid_end_offset
    l_mid_straight = max(0.0, x_mid_tip - l_mid_taper)

    rmid_s = c << gf.components.straight(length=l_mid_straight, cross_section=xs)
    rmid_s.move((0, 0))

    rmid_t = c << gf.components.taper(
        length=l_mid_taper, width1=wg_width, width2=mid_width2, layer=layer
    )
    rmid_t.connect("o1", rmid_s.ports["o2"])

    # External ports
    c.add_port("in_top", port=rt.ports["o1"])
    c.add_port("in_mid", port=rmid_s.ports["o1"])
    c.add_port("in_bot", port=rb.ports["o1"])
    c.add_port("out_top", port=rt.ports["o2"])
    c.add_port("out_bot", port=rb.ports["o2"])

    return c


if __name__ == "__main__":
    c = three_to_two_fanout_v4()
    c.write_gds("three_to_two_fanout_v4.gds")