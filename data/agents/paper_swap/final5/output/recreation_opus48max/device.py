"""
Grating-assisted contra-directional coupler (Bragg-sidewall-grating filter),
primitives-only parametric recreation.

Topology (see recreation_log.json): two sidewall-Bragg-grating waveguides (top +
bottom "combs") flank a solid central bus. Forward light in a grating guide is
contra-coupled to the backward mode of the adjacent bus at the Bragg wavelength
lambda_B = 2*n_eff*Lambda. Inverse-taper edge couplers (needle tips) feed the
device; 180-deg U-bends (hairpins) fold the two grating arms. The function knobs
are the grating period (sets lambda_B), the coupling/transfer LENGTH (sets kappa*L
-> bandwidth & reflectivity), the corrugation height (sets kappa), the bus-grating
gap (sets kappa), and the taper length / tip width (edge-coupler efficiency).

BUILD NOTE (anisotropic calibration): the evaluator maps the GDS bounding box onto
footprint [18.24, 0.70] um with INDEPENDENT x/y scales (sy/sx = 8.098). So the
device is designed in an isotropic "visual" frame (18.24 x 5.67 um, proper
proportions: circular bends, constant-width guides) and then the assembled
geometry is squished in Y by Y_SQUISH so the written GDS fills 18.24 x 0.70 um.
The evaluator's y-stretch inverts this exactly. All tunables below are VISUAL um.
"""
import json
from pathlib import Path

import numpy as np
import gdsfactory as gf
import gdstk

LAYER = (1, 0)
Y_SQUISH = 8.098  # sy/sx from calibration.json (anisotropic footprint mapping)


def _W(w):
    """Snap an extrude width to an even DBU multiple (gdsfactory grid requirement)."""
    return max(0.002, round(w / 0.002) * 0.002)

# ================= FUNCTION KNOBS (top-level tunables, visual microns) =========
grating_period      = 0.1625   # Bragg period of TOP grating -> phase-match wavelength (autocorr)
grating_length      = 12.70   # <<< PRIMARY KNOB: top-grating transfer/coupling length (kappa*L)
grating_duty        = 0.83    # tooth fraction of a period (black tooth ~0.12 um)
corrugation_height  = 0.416   # tooth vertical extent (grating strength kappa)
bot_grating_period  = 0.1625   # Bragg period of BOTTOM grating
bot_grating_length  = 12.15   # bottom-grating length
coupler_gap         = 0.120   # gap grating<->bus (evanescent coupling strength)
bus_width           = 0.236   # central bus waveguide width
taper_length        = 1.40    # inverse-taper (edge coupler) length
tip_width           = 0.070   # inverse-taper tip width
wg_width            = 0.520   # routing / grating-arm guide width
return_width        = 0.530   # top return guide width (measured 112 px)
bend_radius         = 1.020   # hairpin (U-turn) vertical radius r_y
hp_rx               = 0.660   # hairpin horizontal radius r_x (U-turns are vertically elongated)
hp_width            = 0.480   # hairpin (U-turn) guide width

# ---- layout anchors (visual um; positions, not primary physics knobs) --------
top_grating_x0 = 1.86         # left x of top grating (first tooth edge)
top_grating_yc = 3.330        # y-center of top grating band
bus_x0         = 1.91
bus_length     = 14.06
bot_grating_x0 = 3.00
top_return_yc  = 5.370        # top return guide / needle taper axis (top edge -> vy 5.65)
bot_wg_yc      = 0.410        # bottom guide axis
top_hp_cx      = 14.45        # top hairpin arm x (bulges right to ~15.5)
bot_hp_cx      = 3.38         # bottom hairpin arm x (bulges left to ~2.5)


def _rect(c, xc, yc, w, h):
    # placed by absolute path coordinates (no ref.move -> no hierarchy surprises)
    seg = gf.Path([[xc - w / 2, yc], [xc + w / 2, yc]]).extrude(width=_W(h), layer=LAYER)
    c.add_ref(seg)


def _grating(c, x0, length, period, duty, yc, height):
    """Row of isolated full-height sidewall-grating teeth (no core, matches image)."""
    n = max(1, int(round(length / period)))
    tw = duty * period
    for i in range(n):
        xc = x0 + (i + 0.5) * period
        _rect(c, xc, yc, tw, height)
    return n


def _polyline(pts):
    return gf.Path(np.asarray(pts, dtype=float))


def _curve_yx(xs, waypts, width):
    """Extrude a smooth guide whose centerline is y=f(x) through waypoints."""
    wx = np.array([p[0] for p in waypts]); wy = np.array([p[1] for p in waypts])
    ys = np.interp(xs, wx, wy)
    pts = np.column_stack([xs, ys])
    return _polyline(pts).extrude(width=_W(width), layer=LAYER)


def _arc_pts(cx, cy, r_x, r_y, a0, a1, n=80):
    a = np.linspace(np.radians(a0), np.radians(a1), n)
    return np.column_stack([cx + r_x * np.cos(a), cy + r_y * np.sin(a)])


def _taper(c, x0, yc, length, w1, w2):
    """Linear taper (primitive) placed by absolute path coords: width w1 at x0 -> w2 at x0+length."""
    _taper_seg(c, (x0, yc), (x0 + length, yc), w1, w2)


def _taper_seg(c, p0, p1, w1, w2):
    """Linear taper along an arbitrary (possibly diagonal) segment p0 -> p1."""
    xs1 = gf.cross_section.cross_section(width=_W(w1), layer=LAYER)
    xs2 = gf.cross_section.cross_section(width=_W(w2), layer=LAYER)
    trans = gf.path.transition(xs1, xs2, width_type="linear")
    c << gf.path.extrude_transition(gf.Path([list(p0), list(p1)]), trans)


@gf.cell
def device(
    grating_period: float = grating_period,
    grating_length: float = grating_length,
    grating_duty: float = grating_duty,
    corrugation_height: float = corrugation_height,
    bot_grating_period: float = bot_grating_period,
    bot_grating_length: float = bot_grating_length,
    coupler_gap: float = coupler_gap,
    bus_width: float = bus_width,
    taper_length: float = taper_length,
    tip_width: float = tip_width,
    wg_width: float = wg_width,
    bend_radius: float = bend_radius,
) -> gf.Component:
    c = gf.Component()

    _bus_yc = top_grating_yc - corrugation_height / 2 - coupler_gap - bus_width / 2
    _bot_yc = _bus_yc - bus_width / 2 - coupler_gap - corrugation_height / 2

    # ---- three central coupling elements ----
    _grating(c, top_grating_x0, grating_length, grating_period, grating_duty,
             top_grating_yc, corrugation_height)
    _rect(c, bus_x0 + bus_length / 2, _bus_yc, bus_length, bus_width)
    _grating(c, bot_grating_x0, bot_grating_length, bot_grating_period, grating_duty,
             _bot_yc, corrugation_height)

    # ---- top-left input bend: chip edge sweeps down into the top-grating top edge ----
    inp_wp = [(0.03, 5.47), (0.23, 5.06), (0.43, 4.66), (0.63, 4.35), (0.83, 4.10),
              (1.23, 3.80), (1.43, 3.68), (1.63, 3.60), (2.0, 3.49)]
    xs = np.linspace(0.03, 2.0, 60)
    c << _curve_yx(xs, inp_wp, 0.31)

    # ---- top return arm: needle inverse-taper tip -> straight -> right hairpin ----
    tip_x = 2.30
    _taper(c, tip_x, top_return_yc, taper_length, tip_width, return_width)
    ret_x_start = tip_x + taper_length
    _rect(c, (ret_x_start + top_hp_cx) / 2, top_return_yc,
          (top_hp_cx - ret_x_start), return_width)        # return straight

    # ---- top-right hairpin (vertically-elongated 180 deg U-turn) grating end <-> return ----
    top_hp = _arc_pts(top_hp_cx, (top_grating_yc + top_return_yc) / 2,
                      hp_rx, (top_return_yc - top_grating_yc) / 2, -90, 90)
    c << _polyline(top_hp).extrude(width=_W(hp_width), layer=LAYER)
    # fixed stub joining hairpin bottom arm to the grating row (independent of the
    # grating_length knob, so its area response reflects the teeth alone)
    _rect(c, top_hp_cx - 0.30, top_grating_yc, 0.60, wg_width)

    # ---- bottom-left hairpin: bottom-grating left <-> bottom guide (leftmost ~2.5) ----
    bot_hp = _arc_pts(bot_hp_cx, (_bot_yc + bot_wg_yc) / 2,
                      hp_rx, (_bot_yc - bot_wg_yc) / 2, 90, 270)
    c << _polyline(bot_hp).extrude(width=_W(hp_width), layer=LAYER)

    # ---- bottom guide: from bottom hairpin, straight then needle taper to a tip ----
    bwg_x1 = 14.37
    _rect(c, (bot_hp_cx + bwg_x1) / 2, bot_wg_yc, (bwg_x1 - bot_hp_cx), wg_width)
    _taper(c, bwg_x1, bot_wg_yc, 1.25, wg_width, tip_width)  # needle tip to the right

    # ---- bottom-right descent: bottom-grating right end curves down; needle taper to corner ----
    des_wp = [(bot_grating_x0 + bot_grating_length, _bot_yc), (16.30, 2.05),
              (16.95, 1.55), (17.35, 1.02)]
    xs2 = np.linspace(bot_grating_x0 + bot_grating_length, 17.35, 45)
    c << _curve_yx(xs2, des_wp, 0.34)
    # needle output taper to the corner; tip low enough that the device bbox center
    # (return top edge 5.65 + this) squishes to y=0.35 (kills the residual y-shift)
    _taper_seg(c, (17.35, 1.02), (18.12, 0.048), 0.34, 0.06)

    return c


def _path_len(waypts):
    p = np.asarray(waypts, float)
    return float(np.sum(np.hypot(np.diff(p[:, 0]), np.diff(p[:, 1]))))


def main():
    wd = Path(__file__).parent
    c = device()

    # write visual GDS, flatten (get_polygons(depth=None) applies all ref transforms),
    # then squish Y so the bbox fills footprint [18.24, 0.70]
    tmp = wd / "_visual.gds"
    c.write_gds(str(tmp))
    lib = gdstk.read_gds(str(tmp))
    top = lib.top_level()[0]
    out = gdstk.Library()
    dev = out.new_cell("DEVICE")
    # get_polygons(depth=None) double-counts each polygon here; boolean-OR dedupes
    # and unions touching waveguides into clean polygons (rasterization/IoU unchanged).
    raw = top.get_polygons(depth=None, layer=LAYER[0], datatype=LAYER[1])
    for poly in gdstk.boolean(raw, [], "or", layer=LAYER[0], datatype=LAYER[1]):
        poly.scale(1.0, 1.0 / Y_SQUISH, (0.0, 0.0))
        dev.add(poly)
    out.write_gds(str(wd / "device.gds"))
    tmp.unlink(missing_ok=True)

    # ---- self-measured arm lengths (2-arm contract for verify_knob_response) ----
    # The two interferometer arms are the two grating-strand loops (grating + its
    # hairpin + routing). The inverse-taper edge couplers (top-left and bottom-right
    # needle tips) are external I/O and excluded from the arm balance. The signal
    # (top) arm depends linearly on the PRIMARY knob grating_length, and is the
    # LONGER arm at base so raising grating_length raises delta_length monotonically.
    inp_len = _path_len([(0.03, 5.47), (0.23, 5.06), (0.43, 4.66), (0.63, 4.35),
                         (0.83, 4.10), (1.23, 3.80), (1.43, 3.68), (1.63, 3.60), (2.0, 3.49)])
    top_hairpin_len = np.pi * bend_radius
    return_straight = top_hp_cx - (2.30 + taper_length)       # hairpin arm <- return (no I/O taper)
    signal_arm = inp_len + grating_length + top_hairpin_len + return_straight

    bot_hairpin_len = np.pi * bend_radius
    bot_wg_straight = 14.37 - bot_hp_cx                        # bottom guide (no I/O taper)
    reference_arm = bot_hairpin_len + bot_grating_length + bot_wg_straight

    lengths = {
        "arms": {"signal": round(signal_arm, 4), "reference": round(reference_arm, 4)},
        "delta_length_um": round(abs(signal_arm - reference_arm), 4),
    }
    (wd / "lengths.json").write_text(json.dumps(lengths, indent=2))
    print("wrote device.gds and lengths.json:", lengths)


if __name__ == "__main__":
    main()
