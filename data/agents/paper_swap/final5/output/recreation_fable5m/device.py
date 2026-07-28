"""Grating-assisted contra-directional coupler, recreated from device_bw.png.

Primitives only: rectangle, ellipse (+boolean) for the squashed U-bends,
taper, gf.Path + extrude for the adiabatic S-curve leads.
Physical frame: 18.24 x 0.7 um (calibrated absolute scale; the source figure
is vertically stretched, so all y dimensions are true-scale small).

Topology: central bus waveguide; above and below, corrugated waveguides whose
teeth protrude from a narrower spine (attached at the far edge) toward the
bus; each corrugated arm loops back through a 180-degree U-bend into a thick
bar terminated in a point taper, and exits through a thin adiabatic S-lead
(top-left / bottom-right, 180-degree rotationally symmetric).
"""

import numpy as np
import gdsfactory as gf

LAYER = (1, 0)

# ---------------- function-defining tunables (um) ----------------
bus_width_um = 0.0293          # central bus waveguide width
grating_wg_width_um = 0.0506   # corrugation tooth height (full grating depth)
grating_spine_width_um = 0.0420  # uncorrugated spine width (far side of teeth)
gap_bus_grating_um = 0.0167    # bus-to-grating coupling gap
grating_period_um = 0.156072   # mean corrugation period (sets drop wavelength)
grating_duty = 0.7714          # tooth length / period (sets kappa)
n_teeth = 56                   # number of corrugation periods (coupling length)
taper_length_um = 1.514        # point-termination taper length
bar_width_um = 0.069           # loop-back bar waveguide width
sbend_lead_width_um = 0.042    # adiabatic S-curve lead width at the join
sbend_tip_width_um = 0.028     # adiabatic S-curve lead width at the tip
delta_length = 0.0             # extra corrugated-arm (bar) length, um

# chirp: three uniform sections, periods = grating_period_um * factor
chirp_factors = (1.01823, 0.96809, 1.03193)
chirp_counts = (25, 22, 9)

# ---------------- layout constants (um, from the target figure) ----------------
bus_x0 = 1.940
bus_x1 = 15.968
bus_y_center = 0.3557

teeth_x_start = 4.4538
top_lead_in_x0 = 1.970          # top grating solid section start (S-curve join)
bot_lead_out_x1 = 15.790        # bottom grating solid section end (S-curve join)

top_U_cx = 13.926
top_U_rx_o = 1.5746
top_U_rx_i = 1.070
bot_U_cx = 3.9039
bot_U_rx_o = 1.398
bot_U_rx_i = 0.900

top_taper_tip_x = 2.2195
bot_taper_tip_x = 15.6413

bar_band_h_bot = 0.0670          # bottom bar drawn slightly thinner in figure
total_height = 0.70
total_length = 18.24


def _rect(c, x0, y0, x1, y1):
    if x1 <= x0 or y1 <= y0:
        return
    r = c << gf.components.rectangle(size=(x1 - x0, y1 - y0), layer=LAYER)
    r.move((x0, y0))


def _half_annulus(rx_o, ry_o, rx_i, ry_i, side, inner_dy=0.0):
    """Squashed 180-degree U-bend: ellipse annulus cut to one half.

    inner_dy shifts the inner (hole) ellipse vertically relative to the outer,
    since the two waveguides the bend joins have different widths.
    """
    outer = gf.components.ellipse(radii=(rx_o, ry_o), layer=LAYER)
    inner = gf.components.ellipse(radii=(rx_i, ry_i), layer=LAYER)
    innerc = gf.Component()
    ir = innerc << inner
    ir.move((0.0, inner_dy))
    ann = gf.boolean(A=outer, B=innerc, operation="not", layer=LAYER)
    cut = gf.components.rectangle(size=(rx_o + 0.01, 2 * ry_o + 0.02), layer=LAYER)
    cutc = gf.Component()
    cr = cutc << cut
    if side == "right":
        cr.move((-rx_o - 0.01, -ry_o - 0.01))
    else:
        cr.move((0.0, -ry_o - 0.01))
    return gf.boolean(A=ann, B=cutc, operation="not", layer=LAYER)


def _tapered_path(pts, w_start, w_end):
    """Extrude a sampled path with a linearly tapering width."""
    path = gf.Path(pts)
    xs1 = gf.cross_section.cross_section(width=w_start, layer=LAYER)
    xs2 = gf.cross_section.cross_section(width=w_end, layer=LAYER)
    trans = gf.path.transition(xs1, xs2, width_type="linear")
    return gf.path.extrude_transition(path, trans)


def _bezier_pts(pts_ctrl, n=201):
    t = np.linspace(0.0, 1.0, n)[:, None]
    p0, p1, p2, p3 = [np.array(p, dtype=float) for p in pts_ctrl]
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


@gf.cell
def contra_dc() -> gf.Component:
    c = gf.Component()

    bus_y0 = bus_y_center - bus_width_um / 2
    bus_y1 = bus_y_center + bus_width_um / 2

    # grating bands derived from the coupling gap (knobs move real geometry)
    top_g_y0 = bus_y1 + gap_bus_grating_um          # tooth edge nearest bus
    top_g_y1 = top_g_y0 + grating_wg_width_um       # far edge (spine side)
    bot_g_y1 = bus_y0 - gap_bus_grating_um
    bot_g_y0 = bot_g_y1 - grating_wg_width_um
    top_g_c = (top_g_y0 + top_g_y1) / 2
    bot_g_c = (bot_g_y0 + bot_g_y1) / 2
    # spine bands hug the far edge; teeth protrude toward the bus
    top_sp_y0 = top_g_y1 - grating_spine_width_um
    bot_sp_y1 = bot_g_y0 + grating_spine_width_um

    # bar bands
    top_bar_y1 = 0.69753
    top_bar_y0 = top_bar_y1 - bar_width_um
    bot_bar_y0 = 0.0170
    bot_bar_y1 = bot_bar_y0 + bar_band_h_bot

    # ---- central bus ----
    _rect(c, bus_x0, bus_y0, bus_x1, bus_y1)

    # ---- corrugation teeth: three chirped uniform sections ----
    tooth_len = grating_period_um * grating_duty
    x = teeth_x_start
    seg = 0
    left_in_seg = chirp_counts[0]
    for _ in range(n_teeth):
        _rect(c, x, top_g_y0, x + tooth_len, top_g_y1)
        _rect(c, x, bot_g_y0, x + tooth_len, bot_g_y1)
        left_in_seg -= 1
        if left_in_seg == 0 and seg < 2:
            seg += 1
            left_in_seg = chirp_counts[seg]
        x += grating_period_um * chirp_factors[seg]
    teeth_x_end = x - grating_period_um * chirp_factors[seg] + tooth_len

    # ---- solid grating-waveguide sections ----
    # near the teeth the solid sections are full grating height; only the
    # short connectors to the S-leads narrow to the spine width (far edge)
    _rect(c, top_lead_in_x0, top_sp_y0, 2.75, top_g_y1)
    _rect(c, 2.71, top_g_y0, teeth_x_start - 0.008, top_g_y1)
    _rect(c, teeth_x_end + 0.004, top_g_y0, 14.825, top_g_y1)
    _rect(c, 3.45, bot_g_y0, teeth_x_start - 0.008, bot_g_y1)
    _rect(c, teeth_x_end + 0.004, bot_g_y0, 14.836, bot_g_y1)
    _rect(c, 14.80, bot_g_y0, bot_lead_out_x1, bot_sp_y1)

    # ---- U-bends (squashed ellipse half-annuli, inner hole offset) ----
    top_cy = (top_bar_y1 + top_sp_y0) / 2
    top_ry_o = top_bar_y1 - top_cy
    top_ry_i = (top_bar_y0 - top_g_y1) / 2
    top_cy_i = (top_bar_y0 + top_g_y1) / 2
    u_t = c << _half_annulus(top_U_rx_o, top_ry_o, top_U_rx_i, top_ry_i,
                             "right", inner_dy=top_cy_i - top_cy)
    u_t.move((top_U_cx, top_cy))

    bot_cy = (bot_bar_y0 + bot_sp_y1) / 2
    bot_ry_o = bot_cy - bot_bar_y0
    bot_ry_i = (bot_g_y0 - bot_bar_y1) / 2
    bot_cy_i = (bot_g_y0 + bot_bar_y1) / 2
    u_b = c << _half_annulus(bot_U_rx_o, bot_ry_o, bot_U_rx_i, bot_ry_i,
                             "left", inner_dy=bot_cy_i - bot_cy)
    u_b.move((bot_U_cx, bot_cy))

    # ---- bar waveguides with point-taper terminations ----
    tp = c << gf.components.taper(length=taper_length_um, width1=0.010,
                                  width2=0.068, layer=LAYER)
    tp.move((top_taper_tip_x - delta_length, 0.664))
    _rect(c, top_taper_tip_x - delta_length + taper_length_um - 0.005, top_bar_y0, top_U_cx, top_bar_y1)

    bot_taper_len = 1.460
    _rect(c, bot_U_cx, bot_bar_y0, bot_taper_tip_x - bot_taper_len + 0.005, bot_bar_y1)
    tb = c << gf.components.taper(length=bot_taper_len, width1=0.010,
                                  width2=0.066, layer=LAYER)
    tb.mirror_x()
    tb.move((bot_taper_tip_x, 0.0508))

    # ---- adiabatic S-curve leads (width tapers toward the free tip) ----
    top_pts = _bezier_pts(
        [(0.0, total_height - sbend_tip_width_um / 2),
         (0.28, 0.565), (1.2834, 0.4160), (2.70, 0.4175)])
    c << _tapered_path(top_pts, sbend_tip_width_um, sbend_lead_width_um)

    # bottom lead: measured quartic centerline, clamped so the stroke ends at y=0
    tail_end_x = 17.74
    xs = np.linspace(15.75, tail_end_x, 200)
    poly = (0.047277620360428325, -0.22665563327935423, 0.2931340517528031,
            -0.1741633293748328, 0.30168471625391463)
    ys = np.polyval(poly, xs - 15.60)  # poly domain is anchored at x=15.60
    ys = np.minimum(np.maximum(ys, sbend_tip_width_um / 2), bot_g_c)
    c << _tapered_path(np.column_stack([xs, ys]),
                       sbend_lead_width_um, sbend_tip_width_um)
    # faint tail tip continues to the frame bottom in the source figure;
    # a sliver at the tail tip anchors the bounding box there
    _rect(c, tail_end_x - 0.016, 0.0, tail_end_x, 0.045)

    return c


def _measure_lengths() -> dict:
    """Arm lengths measured from the geometry parameters at build time."""
    import json

    bus_len = bus_x1 - bus_x0
    # corrugated arm: S-lead + solid sections + grating + U-bend + bar + taper
    top_pts = _bezier_pts(
        [(0.0, total_height - sbend_tip_width_um / 2),
         (0.28, 0.565), (1.2834, 0.4160), (2.70, 0.4175)])
    lead_len = float(np.sum(np.hypot(*np.diff(top_pts, axis=0).T)))
    solid_len = 14.825 - 2.70
    th = np.linspace(0.0, np.pi, 400)
    rx_m = (top_U_rx_o + top_U_rx_i) / 2
    ry_m = 0.126  # mid-annulus vertical radius
    u_len = float(np.sum(np.hypot(np.diff(rx_m * np.sin(th)), np.diff(ry_m * np.cos(th)))))
    bar_len = top_U_cx - (top_taper_tip_x - delta_length)
    grating_arm = lead_len + solid_len + u_len + bar_len
    arms = {"bus": bus_len, "grating_arm": grating_arm}
    payload = {"arms": arms, "delta_length_um": arms["grating_arm"] - arms["bus"]}
    with open("lengths.json", "w") as fh:
        json.dump(payload, fh, indent=2)
    return payload


if __name__ == "__main__":
    comp = contra_dc()
    comp.write_gds("device.gds", with_metadata=False)
    _measure_lengths()
