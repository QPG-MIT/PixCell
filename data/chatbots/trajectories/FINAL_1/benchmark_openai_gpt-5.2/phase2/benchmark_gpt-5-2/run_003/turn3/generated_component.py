import gdsfactory as gf


def snap_even_dbu(width_um: float) -> float:
    """Snap a width (in um) to an even number of dbu (required by SymmetricalCrossSection)."""
    dbu = gf.kcl.dbu  # um per database unit (e.g., 0.001 um for 1 nm)
    n = int(round(width_um / dbu))
    if n < 2:
        n = 2
    if n % 2 == 1:
        n += 1
    return n * dbu


def bezier_s_bend(
    dx: float,
    dy: float,
    *,
    a: float = 0.55,
    b: float = 0.80,
    npoints: int = 201,
) -> gf.Path:
    """S-bend with horizontal tangents at both ends (Bezier)."""
    # Horizontal tangent at start: P0.y == P1.y
    # Horizontal tangent at end:   P2.y == P3.y
    cps = [(0.0, 0.0), (a * dx, 0.0), (b * dx, dy), (dx, dy)]
    return gf.path.bezier(control_points=cps, npoints=npoints)


@gf.cell
def outer_arm_outward_taper(
    *,
    length_pre: float,
    length_bend: float,
    length_out: float,
    dy_inner_edge: float,
    w_in: float,
    w_out: float,
    layer: tuple[int, int] = (1, 0),
    # +1 for top (grows upward), -1 for bottom (grows downward)
    grow_sign: int = +1,
    # Bezier shaping (larger b delays the move until later -> closer to your target)
    bezier_a: float = 0.55,
    bezier_b: float = 0.82,
) -> gf.Component:
    """
    Outer arm built so the taper grows *outward* (inner edge stays pinned),
    then an S-bend that finishes horizontal, then a final horizontal straight.
    """
    c = gf.Component()

    w_in = snap_even_dbu(w_in)
    w_out = snap_even_dbu(w_out)

    # Offset cross-sections: path follows the INNER EDGE, geometry grows outward
    xs_in = gf.cross_section.strip(width=w_in, layer=layer, offset=grow_sign * (w_in / 2))
    xs_out = gf.cross_section.strip(width=w_out, layer=layer, offset=grow_sign * (w_out / 2))

    # Part A: straight + S-bend, with width transition reaching w_out at the end of the bend
    p = gf.path.straight(length=length_pre)
    p.append(
        bezier_s_bend(
            dx=length_bend,
            dy=dy_inner_edge,
            a=bezier_a,
            b=bezier_b,
            npoints=301,
        )
    )
    t = gf.path.transition(xs_in, xs_out, width_type="linear")
    core = c << gf.path.extrude_transition(p, t)

    # Part B: final horizontal output
    out = c << gf.path.extrude(gf.path.straight(length=length_out), cross_section=xs_out)
    out.connect("o1", core.ports["o2"])

    c.add_port("o1", port=core.ports["o1"])
    c.add_port("o2", port=out.ports["o2"])
    return c


@gf.cell
def recreated_device_v4(
    # Footprint target
    length_total: float = 40.0,
    height_total: float = 1.7,
    # X segmentation: keep parallel long, then smooth split, then flat horizontal
    length_pre: float = 26.0,     # long straight/taper section
    length_bend: float = 8.0,     # curvature/split zone
    length_out: float = 6.0,      # final horizontal
    # Outer widths
    w_outer_in: float = 0.18,
    w_outer_out: float = 0.38,
    # Left centerline offset (same meaning as your v3): top centerline at +y_outer_left
    y_outer_left: float = 0.32,
    # Bend shaping (push closer to the “late” curvature of the target)
    bezier_a: float = 0.55,
    bezier_b: float = 0.86,
    # Middle needle (thin wedge that ends before split)
    length_mid: float = 24.0,
    w_mid_in: float = 0.08,
    w_mid_out: float = 0.002,  # very pointy; snapped to even dbu
    mid_y0: float = -0.01,     # vertical placement of needle at x=0
    mid_dy: float = -0.05,     # end droop
    mid_bezier_a: float = 0.70,
    mid_bezier_b: float = 0.93,
    layer: tuple[int, int] = (1, 0),
) -> gf.Component:
    c = gf.Component()

    # --- sanity / lengths ---
    if abs((length_pre + length_bend + length_out) - length_total) > 1e-9:
        raise ValueError("length_pre + length_bend + length_out must equal length_total.")

    w_outer_in = snap_even_dbu(w_outer_in)
    w_outer_out = snap_even_dbu(w_outer_out)
    w_mid_in = snap_even_dbu(w_mid_in)
    w_mid_out = snap_even_dbu(w_mid_out)

    # Convert your previous "centerline y at left" into "inner-edge y at left"
    # because we now pin the inner edge via cross_section offset.
    y_inner_left = y_outer_left - w_outer_in / 2.0

    # At the far right, enforce the total height by pinning the OUTER edges at +/- height_total/2.
    # For the top arm inner edge: y_inner_right + w_outer_out = +height_total/2
    y_inner_right = height_total / 2.0 - w_outer_out

    dy_inner = y_inner_right - y_inner_left  # top inner edge shift; bottom is negative of this

    # --- Outer arms ---
    arm_top = outer_arm_outward_taper(
        length_pre=length_pre,
        length_bend=length_bend,
        length_out=length_out,
        dy_inner_edge=+dy_inner,
        w_in=w_outer_in,
        w_out=w_outer_out,
        layer=layer,
        grow_sign=+1,
        bezier_a=bezier_a,
        bezier_b=bezier_b,
    )
    arm_bot = outer_arm_outward_taper(
        length_pre=length_pre,
        length_bend=length_bend,
        length_out=length_out,
        dy_inner_edge=-dy_inner,
        w_in=w_outer_in,
        w_out=w_outer_out,
        layer=layer,
        grow_sign=-1,
        bezier_a=bezier_a,
        bezier_b=bezier_b,
    )

    top = c << arm_top
    bot = c << arm_bot

    # Move references so their *inner edges* start at +/- y_inner_left
    top.move((0, +y_inner_left))
    bot.move((0, -y_inner_left))

    # --- Middle needle: delayed droop Bezier + linear taper to near-zero ---
    xs_mid1 = gf.cross_section.strip(width=w_mid_in, layer=layer)
    xs_mid2 = gf.cross_section.strip(width=w_mid_out, layer=layer)
    tmid = gf.path.transition(xs_mid1, xs_mid2, width_type="linear")

    p_mid = bezier_s_bend(
        dx=length_mid,
        dy=mid_dy,
        a=mid_bezier_a,
        b=mid_bezier_b,
        npoints=301,
    )
    mid = c << gf.path.extrude_transition(p_mid, tmid)
    mid.move((0, mid_y0))

    # --- Ports ---
    c.add_port("in_top", port=top.ports["o1"])
    c.add_port("in_mid", port=mid.ports["o1"])
    c.add_port("in_bot", port=bot.ports["o1"])
    c.add_port("out_top", port=top.ports["o2"])
    c.add_port("out_bot", port=bot.ports["o2"])

    return c


if __name__ == "__main__":
    d = recreated_device_v4()
    d.show()
    d.write_gds("recreated_device_v4.gds")