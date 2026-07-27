import numpy as np
import gdsfactory as gf

LAYER = (1, 0)


def snap_to_grid(v: float, grid: float = 1e-3) -> float:
    """Snap scalar to a manufacturing grid (um). Default 1 nm grid."""
    return float(np.round(v / grid) * grid)


def snap_points_to_grid(pts, grid: float = 1e-3):
    a = np.asarray(pts, dtype=float)
    a = np.round(a / grid) * grid
    return [tuple(xy) for xy in a.tolist()]


def cubic_bezier_points(control_points, npoints: int = 101):
    """Sampled (x, y) points along a cubic Bezier curve."""
    if len(control_points) != 4:
        raise ValueError("cubic_bezier_points requires exactly 4 control points.")
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = control_points

    t = np.linspace(0.0, 1.0, npoints)
    mt = 1.0 - t

    x = (mt**3) * x0 + 3 * (mt**2) * t * x1 + 3 * mt * (t**2) * x2 + (t**3) * x3
    y = (mt**3) * y0 + 3 * (mt**2) * t * y1 + 3 * mt * (t**2) * y2 + (t**3) * y3
    return list(zip(x.tolist(), y.tolist()))


@gf.cell
def taper_transition_offset(
    length: float = 10.0,
    width1: float = 0.06,
    width2: float = 0.22,
    offset1: float = 0.0,
    offset2: float = 0.0,
    layer=LAYER,
    width_type: str = "sine",
) -> gf.Component:
    """Taper that transitions BOTH width and lateral offset (to anchor one edge)."""
    xs1 = gf.cross_section.strip(width=width1, layer=layer, offset=offset1)
    xs2 = gf.cross_section.strip(width=width2, layer=layer, offset=offset2)
    trans = gf.path.transition(xs1, xs2, width_type=width_type)
    p = gf.path.straight(length=length)
    return gf.path.extrude_transition(p, trans)


@gf.cell
def fanout_bezier(
    dx: float = 6.0,
    dy: float = 0.4,
    ctrl: float = 0.35,
    npoints: int = 121,
    grid: float = 1e-3,
    cross_section=None,
) -> gf.Component:
    """
    Smooth fan-out using a sampled cubic Bezier.

    IMPORTANT: we force the first/last segment to be EXACTLY horizontal and snap
    points to grid so the resulting ports are exactly 0/180 degrees (no tiny
    rotation during .connect -> avoids off-grid instance errors).
    """
    dx = snap_to_grid(dx, grid)
    dy = snap_to_grid(dy, grid)

    cps = [(0.0, 0.0), (dx * ctrl, 0.0), (dx * (1 - ctrl), dy), (dx, dy)]
    pts = cubic_bezier_points(cps, npoints=npoints)

    # Snap to grid first
    pts = snap_points_to_grid(pts, grid=grid)

    # Enforce exact horizontal tangents at both ends (ports use first/last segment angle)
    eps = max(5 * grid, dx * 1e-4)  # small but non-zero
    eps = snap_to_grid(eps, grid)

    pts[0] = (0.0, 0.0)
    pts[1] = (eps, 0.0)                    # guarantees start segment has dy=0
    pts[-2] = (dx - eps, dy)               # guarantees end segment has dy=0
    pts[-1] = (dx, dy)

    p = gf.Path(pts)
    return gf.path.extrude(p, cross_section=cross_section)


@gf.cell
def three_waveguides_split_like_png_v5(
    # Footprint target
    length_total: float = 40.0,
    height_total: float = 1.7,
    layer=LAYER,
    # Widths
    w_mid: float = 0.14,
    w_outer: float = 0.22,
    w_outer_start: float = 0.06,
    # Coupling-region gap control
    gap_cpl: float = 0.18,
    # Length partition
    ltaper_outer: float = 18.0,
    lcpl: float = 12.0,
    lfan_dx: float = 6.0,
    # Output placement
    y_out: float = 0.73,
    # Center termination
    center_end_offset: float = 2.5,
    # Shape controls
    width_type: str = "sine",
    bezier_ctrl: float = 0.35,
    bezier_npoints: int = 121,
    grid: float = 1e-3,
) -> gf.Component:
    c = gf.Component()

    # Snap key inputs to grid to reduce numerical drift
    length_total = snap_to_grid(length_total, grid)
    height_total = snap_to_grid(height_total, grid)
    ltaper_outer = snap_to_grid(ltaper_outer, grid)
    lcpl = snap_to_grid(lcpl, grid)
    lfan_dx = snap_to_grid(lfan_dx, grid)
    y_out = snap_to_grid(y_out, grid)
    center_end_offset = snap_to_grid(center_end_offset, grid)

    half_h = height_total / 2
    if abs(y_out) + w_outer / 2 > half_h + 1e-6:
        raise ValueError("y_out/w_outer exceed the requested height_total footprint.")

    # Keep inner edge of outer guides fixed in coupling region
    y_inner = snap_to_grid((w_mid / 2) + gap_cpl, grid)

    # Outer centerline in coupling region (width = w_outer)
    y_cpl_center = snap_to_grid(y_inner + (w_outer / 2), grid)

    # Offsets for anchored taper
    off_top_start = snap_to_grid(y_inner + (w_outer_start / 2), grid)
    off_top_end = snap_to_grid(y_inner + (w_outer / 2), grid)

    off_bot_start = snap_to_grid(-y_inner - (w_outer_start / 2), grid)
    off_bot_end = snap_to_grid(-y_inner - (w_outer / 2), grid)

    # Fan-out delta from coupling centerline to output centerline
    dy_fan = snap_to_grid(y_out - y_cpl_center, grid)
    if dy_fan <= 0:
        raise ValueError("Need y_out > y_cpl_center for outward fan-out.")

    # Length budgeting
    lout = snap_to_grid(length_total - (ltaper_outer + lcpl + lfan_dx), grid)
    if lout <= 0:
        raise ValueError("Invalid lengths: need length_total > ltaper_outer + lcpl + lfan_dx.")

    x_fan_start = ltaper_outer + lcpl
    x_mid_end = snap_to_grid(x_fan_start - center_end_offset, grid)
    if x_mid_end <= 0:
        raise ValueError("center_end_offset too large; center waveguide would be non-positive length.")

    # Cross-sections
    xs_mid = gf.cross_section.strip(width=w_mid, layer=layer)
    xs_outer = gf.cross_section.strip(width=w_outer, layer=layer)

    # -------------------------
    # TOP: anchored taper -> straight -> bezier fanout -> straight
    # -------------------------
    top_taper = c << taper_transition_offset(
        length=ltaper_outer,
        width1=w_outer_start,
        width2=w_outer,
        offset1=off_top_start,
        offset2=off_top_end,
        layer=layer,
        width_type=width_type,
    )

    top_cpl = c << gf.components.straight(length=lcpl, cross_section=xs_outer)
    top_cpl.connect("o1", top_taper.ports["o2"])

    top_fan = c << fanout_bezier(
        dx=lfan_dx,
        dy=dy_fan,
        ctrl=bezier_ctrl,
        npoints=bezier_npoints,
        grid=grid,
        cross_section=xs_outer,
    )
    top_fan.connect("o1", top_cpl.ports["o2"])

    top_out = c << gf.components.straight(length=lout, cross_section=xs_outer)
    top_out.connect("o1", top_fan.ports["o2"])

    # -------------------------
    # BOTTOM: anchored taper -> straight -> bezier fanout (down) -> straight
    # -------------------------
    bot_taper = c << taper_transition_offset(
        length=ltaper_outer,
        width1=w_outer_start,
        width2=w_outer,
        offset1=off_bot_start,
        offset2=off_bot_end,
        layer=layer,
        width_type=width_type,
    )

    bot_cpl = c << gf.components.straight(length=lcpl, cross_section=xs_outer)
    bot_cpl.connect("o1", bot_taper.ports["o2"])

    bot_fan = c << fanout_bezier(
        dx=lfan_dx,
        dy=-dy_fan,
        ctrl=bezier_ctrl,
        npoints=bezier_npoints,
        grid=grid,
        cross_section=xs_outer,
    )
    bot_fan.connect("o1", bot_cpl.ports["o2"])

    bot_out = c << gf.components.straight(length=lout, cross_section=xs_outer)
    bot_out.connect("o1", bot_fan.ports["o2"])

    # -------------------------
    # CENTER: constant-width stub
    # -------------------------
    mid = c << gf.components.straight(length=x_mid_end, cross_section=xs_mid)

    # External ports
    c.add_port("o1", port=top_taper.ports["o1"])  # top input
    c.add_port("o2", port=mid.ports["o1"])        # mid input
    c.add_port("o3", port=bot_taper.ports["o1"])  # bottom input
    c.add_port("o4", port=top_out.ports["o2"])    # top output
    c.add_port("o5", port=bot_out.ports["o2"])    # bottom output

    return c


if __name__ == "__main__":
    c = three_waveguides_split_like_png_v5()
    c.write_gds("recreated_device_v5.gds")