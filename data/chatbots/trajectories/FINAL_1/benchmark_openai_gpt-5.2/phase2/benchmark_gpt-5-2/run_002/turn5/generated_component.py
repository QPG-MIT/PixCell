import numpy as np
import gdsfactory as gf


def _smoothstep5(u: np.ndarray) -> np.ndarray:
    """Quintic smootherstep (C2 at endpoints) for u in [0, 1]."""
    return 10 * u**3 - 15 * u**4 + 6 * u**5


def _sbend_quintic_shoulder_points(
    dx: float,
    dy: float,
    n: int = 501,
    shoulder_frac: float = 0.20,
    bias: float = 2.4,
) -> list[tuple[float, float]]:
    """
    S-bend from (0,0) to (dx,dy), horizontal tangents and zero curvature at endpoints.

    Improvements vs a plain quintic:
    - 'shoulder_frac' creates flat shoulders at start and end of the bend region
      (still C2 at the shoulder boundaries because smoothstep5 has y'=y''=0 at u=0,1).
    - 'bias' (>1) pushes most of the motion later inside the active interval.
    - cosine-spaced sampling clusters points near shoulder boundaries (reduces apparent kinks).
    """
    if dx <= 0:
        raise ValueError(f"dx must be > 0, got {dx}")
    if not (0.0 <= shoulder_frac < 0.5):
        raise ValueError(f"shoulder_frac must be in [0, 0.5), got {shoulder_frac}")
    if bias <= 0:
        raise ValueError(f"bias must be > 0, got {bias}")
    if n < 20:
        raise ValueError("n too small; use n>=20 for a decent polyline.")

    s0 = shoulder_frac
    active = 1.0 - 2.0 * s0
    if active <= 0:
        raise ValueError("shoulder_frac too large; no active bend region remains.")

    # Cosine spacing on [0,1] (clusters near ends)
    m = max(10, n - 4)
    t01 = 0.5 - 0.5 * np.cos(np.linspace(0.0, 1.0, m) * np.pi)

    # Map to [s0, 1-s0] and add explicit endpoints/shoulder points
    t = np.concatenate(([0.0, s0], s0 + active * t01, [1.0 - s0, 1.0]))
    t = np.unique(np.clip(t, 0.0, 1.0))

    # Active-interval coordinate u in [0,1], clamped outside shoulders
    u = (t - s0) / active
    u = np.clip(u, 0.0, 1.0)

    # Bias motion later (u**bias) while preserving C2 endpoints
    u_biased = u**bias
    s = _smoothstep5(u_biased)

    x = dx * t
    y = dy * s
    return list(zip(x.tolist(), y.tolist()))


@gf.cell
def three_to_two_fanout_v5(
    footprint_um: tuple[float, float] = (40.0, 1.7),
    layer: tuple[int, int] = (1, 0),
    wg_width: float = 0.18,
    gap_in: float = 0.18,
    # X partition (must sum to footprint_um[0])
    l_pre: float = 24.0,
    l_curve: float = 13.0,
    l_post: float = 3.0,
    # Bend shaping
    bend_shoulder_frac: float = 0.20,  # flat shoulders within l_curve
    bend_bias: float = 2.4,            # >1 pushes bend later
    bend_npoints: int = 501,
    # Middle arm wedge
    l_mid_taper: float = 13.0,         # longer wedge, starts earlier
    mid_width2: float = 0.03,
    mid_tip_length: float = 0.40,      # small constant-width tip after taper
    mid_end_offset: float = 0.20,      # tip ends slightly before bend starts
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
        y_out_margin = wg_width / 2  # keep edges inside the footprint

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
        sb_pts = _sbend_quintic_shoulder_points(
            dx=l_curve,
            dy=dy_local,
            n=bend_npoints,
            shoulder_frac=bend_shoulder_frac,
            bias=bend_bias,
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

    # MIDDLE arm: straight -> long taper -> short thin tip; ends just before bend start
    x_bend_start = l_pre
    x_mid_tip = x_bend_start - mid_end_offset

    l_mid_straight = max(0.0, x_mid_tip - l_mid_taper - mid_tip_length)

    rmid_s = c << gf.components.straight(length=l_mid_straight, cross_section=xs)
    rmid_s.move((0, 0))

    rmid_t = c << gf.components.taper(
        length=l_mid_taper, width1=wg_width, width2=mid_width2, layer=layer
    )
    rmid_t.connect("o1", rmid_s.ports["o2"])

    if mid_tip_length > 0:
        xs_tip = gf.cross_section.cross_section(width=mid_width2, layer=layer)
        rmid_tip = c << gf.components.straight(length=mid_tip_length, cross_section=xs_tip)
        rmid_tip.connect("o1", rmid_t.ports["o2"])

    # External ports
    c.add_port("in_top", port=rt.ports["o1"])
    c.add_port("in_mid", port=rmid_s.ports["o1"])
    c.add_port("in_bot", port=rb.ports["o1"])
    c.add_port("out_top", port=rt.ports["o2"])
    c.add_port("out_bot", port=rb.ports["o2"])

    return c


if __name__ == "__main__":
    c = three_to_two_fanout_v5()
    c.write_gds("three_to_two_fanout_v5.gds")