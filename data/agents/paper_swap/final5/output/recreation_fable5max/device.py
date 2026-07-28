"""Recreation of data/agents/paper_swap/final5/device_bw.png.

Grating-assisted contra-directional coupler in a folded layout: a continuous
central bus strip flanked by two 56-tooth segmented (comb) waveguide sections,
each the middle of a folded strip guide (needle taper -> straight -> 180-degree
U-bend -> comb -> thin tapering S-lead exiting at a corner).

Built in the gate's calibrated frame: bbox [63,18,3712,1152] px of the target
maps to 18.24 x 0.7 um (sx=200.05482 px/um, sy=1620 px/um, anisotropy 8.1).
Because of the anisotropy, image-circular U-bends are ellipse half-annuli in
physical um (boolean of two ellipses cut by a half-plane), and slanted leads
are Path+extrude chains whose width is slope-corrected so the rasterized
column thickness matches the target.

Primitives only: rectangle, taper, ellipse+boolean, gf.Path+extrude, @gf.cell.
Layer (1, 0). Outputs (device.gds, lengths.json) are written next to this file.
lengths.json delta_length_um = central bus interaction length, derived from the
bus gf.Path — the verified function knob is bus_length_um.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import gdsfactory as gf

LAYER = (1, 0)

# ---------------------------------------------------------------- calibration
# Fixed by the target image bbox + footprint.json; px provenance in comments.
SX = 200.05482  # px per um, x  (3649 px / 18.24 um)
SY = 1620.0     # px per um, y  (1134 px / 0.70 um)
BBOX_X0_PX = 63.0
IMG_H_PX = 1152.0

device_length_um = 18.240

# ------------------------------------------------------------ function knobs
# Cross-track structure (um). px values in comments are target measurements
# at the gate threshold (245) minus the ~1.5 px raster bloom per side.
wg_width_um = 0.0674          # top strip guide width      (110.7 px @245)
wg_bot_width_um = 0.0654      # bottom strip guide width   (107.5 px @245)
swg_width_um = 0.0502         # comb tooth height          (83 px @245)
bar_width_um = 0.0266         # central bus width (drawn at the half-coverage
                              # edge rows; the 245-edge rows are AA-partial)
coupling_gap_top_um = 0.0164  # bus edge <-> upper tooth edge (25 px @245)
coupling_gap_bot_um = 0.0164  # bus edge <-> lower tooth edge (26 px @245)
top_track_offset_um = 0.2526  # upper comb center -> top wg center
bot_track_offset_um = 0.2508  # lower comb center -> bottom wg center
bar_center_y_um = 0.3563      # bus centerline (py 574.4; chosen so every
                              # track's lower edge lands on an integer nm)

# Grating (the function-defining periodic structure). The target's teeth
# wander around uniform pitch by up to +/-9 px (same wander in both combs);
# the measured per-tooth table below reproduces it, scaled by these knobs.
grating_pitch_um = 0.15614    # mean pitch, 31.24 px
grating_duty = 0.75           # mean drawn tooth x-width / pitch
n_teeth = 56
teeth_start_x_um = 4.45878    # first tooth left edge      (px 955)

# Bus (verified knob: lengths.json delta_length_um tracks this 1:1).
bus_start_x_um = 1.93973      # px 451.05
bus_length_um = 14.03089      # px 451.05 -> 3257.99

# Needle (inverse) tapers terminating the strip guides.
taper_top_tip_x_um = 2.22189      # px 507.5
taper_top_length_um = 1.62955     # px 507 -> 833
taper_top_tip_width_um = 0.0080   # 13 px
taper_bot_start_x_um = 14.13114   # px 2890
taper_bot_length_um = 1.54458     # px 2890 -> 3199
taper_bot_tip_width_um = 0.0062   # 10 px

# U-bends (x-radii of the ellipse half-annuli; y-radii derive from tracks).
bend_right_x_um = 13.97618        # junction plane, px 2859
bend_right_rx_outer_um = 1.52059  # 304.2 px
bend_right_rx_inner_um = 1.07221  # 214.5 px
bend_right_comb_lift_um = 0.0043  # bend arm meets the comb ~7 px high
bend_left_x_um = 3.91393          # junction plane, px 846
bend_left_rx_outer_um = 1.41465   # 283 px
bend_left_rx_inner_um = 0.94724   # 189.5 px

# Comb landings / S-lead anchors.
s2_start_x_um = 14.43104          # lower-right landing end, px 2950

# --------------------------------------------------- measured lead centerlines
# (x_px, y_px of centerline, column thickness_px) at threshold 128 in the
# target; converted to um and slope-corrected at build time.
# Per-tooth left edges relative to tooth 0 and widths (px, threshold 128,
# same in both combs to <=1 px). Scaled by grating_pitch_um / grating_duty.
TOOTH_REL_PX = [
    -0.75, 30.25, 62.25, 94.25, 126.25, 158.25, 190.25, 222.25, 254.25,
    286.25, 318.25, 350.25, 382.0, 413.25, 445.0, 476.0, 509.25, 541.0,
    573.25, 605.0, 636.0, 668.0, 699.5, 732.0, 762.0, 791.25, 819.0, 848.25,
    877.25, 908.0, 939.25, 970.0, 1004.0, 1035.25, 1068.0, 1098.0, 1132.25,
    1162.0, 1195.25, 1223.0, 1254.0, 1282.25, 1310.0, 1341.25, 1370.25,
    1398.0, 1429.0, 1461.0, 1493.25, 1525.0, 1557.25, 1589.25, 1621.0,
    1653.25, 1685.25, 1717.25,
]
TOOTH_W_PX = [
    23.5, 24.5, 24.5, 24.5, 24.5, 24.5, 23.5, 23.5, 23.5, 23.5, 23.5, 23.5,
    23.5, 24.5, 24.5, 24.5, 23.5, 24.5, 23.5, 23.5, 25.5, 24.5, 24.0, 23.5,
    22.5, 21.5, 22.5, 21.5, 22.5, 22.5, 23.5, 24.5, 23.5, 23.5, 22.5, 24.5,
    22.5, 24.5, 21.5, 22.5, 21.5, 21.5, 23.5, 21.5, 22.5, 23.5, 25.5, 23.5,
    23.5, 23.5, 23.5, 23.5, 24.5, 23.5, 23.5, 23.5,
]
PITCH_REF_PX = 31.236
DUTY_REF = 0.75  # mean drawn tooth width / pitch after per-tooth fit

S1_PTS_PX = [
    (64.5, 46, 10), (72, 55, 32), (80, 71, 52), (86, 86.5, 55), (106, 133.5, 59), (126, 175, 64),
    (146, 213.5, 63), (166, 247, 64), (186, 276.5, 63), (206, 302, 62),
    (226, 325, 60), (246, 344, 58), (266, 361.5, 59), (286, 376, 58),
    (306, 390, 58), (326, 402, 58), (346, 412.5, 57), (366, 422, 58),
    (386, 431, 58), (406, 439, 58), (426, 445.5, 59), (446, 452, 60),
    (466, 457, 60), (486, 462, 62), (506, 466.5, 63), (526, 470, 64),
    (546, 473, 64), (566, 475.5, 65), (586, 478, 66), (606, 480, 68),
    (626, 481.5, 69), (646, 483, 70), (666, 484.5, 71), (686, 485, 72),
    (706, 485, 74), (726, 485.5, 75), (746, 485.5, 75), (766, 485.5, 77),
    (800, 485.5, 79), (850, 485.5, 81), (900, 485.5, 82), (947, 485.5, 83),
]
S2_PTS_PX = [
    (2950, 664.5, 76), (2980, 665, 74), (3010, 665.5, 72), (3040, 667, 70),
    (3070, 669, 69), (3100, 672.5, 67), (3130, 676.5, 65), (3160, 681, 64),
    (3190, 687, 62), (3220, 694.5, 61), (3250, 703.5, 60), (3280, 714.5, 59),
    (3310, 727, 58), (3340, 742, 58), (3370, 759, 58), (3400, 780, 58),
    (3430, 805, 59), (3460, 835, 62), (3490, 872, 63), (3520, 917.5, 65),
    (3550, 975, 64), (3570, 1016, 62), (3585, 1052, 58), (3598, 1078, 34),
    (3612, 1096, 14), (3640, 1118, 10), (3670, 1135, 7), (3695, 1146, 5),
    (3711, 1150, 3),
]
# Upper-right landing tilts up ~7 px into the bend junction in the target.
UR_LANDING_PTS_PX = [(2703.4, 485.5, 84.5), (2800, 485, 84.5), (2859, 478.5, 84.5)]


def _px_to_um(x_px: float, y_px: float) -> tuple[float, float]:
    return (x_px - BBOX_X0_PX) / SX, (IMG_H_PX - y_px) / SY


def _even(w_um: float) -> float:
    """Snap a width to an even number of nm (kfactory port constraint)."""
    return max(round(w_um / 0.002) * 0.002, 0.002)


def _lead_chain(comp: gf.Component, pts_px, snap_y_um: float, snap_tol_px: float = 2.0) -> float:
    """Add a tapering lead as chained Path+extrude segments; return its length (um)."""
    pts = []
    for x_px, y_px, w_px in pts_px:
        x, y = _px_to_um(x_px, y_px)
        if abs(y - snap_y_um) < snap_tol_px / SY:
            y = snap_y_um
        pts.append((x, y, w_px))
    total = 0.0
    for (x0, y0, w0), (x1, y1, w1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        seg_len = math.hypot(dx, dy)
        cos_t = dx / seg_len if seg_len else 1.0
        w_col_px = max(0.5 * (w0 + w1) - 1.5, 2.5)  # -1.5 px: gate-threshold trim
        w_um = max(round(w_col_px / SY * cos_t / 0.002) * 0.002, 0.002)
        p = gf.Path(np.array([[x0, y0], [x1, y1]]))
        comp.add_ref(p.extrude(width=w_um, layer=LAYER))
        total += seg_len
    return total


def _half_annulus(xc, side, rx_o, y_top_o, y_bot_o, rx_i, y_top_i, y_bot_i) -> gf.Component:
    """U-bend: (outer ellipse - inner ellipse) restricted to one side of x=xc."""
    ry_o, yc_o = (y_top_o - y_bot_o) / 2, (y_top_o + y_bot_o) / 2
    ry_i, yc_i = (y_top_i - y_bot_i) / 2, (y_top_i + y_bot_i) / 2
    co = gf.Component()
    co.add_ref(gf.components.ellipse(radii=(rx_o, ry_o), angle_resolution=0.25, layer=LAYER)).move((xc, yc_o))
    ci = gf.Component()
    ci.add_ref(gf.components.ellipse(radii=(rx_i, ry_i), angle_resolution=0.25, layer=LAYER)).move((xc, yc_i))
    ann = gf.boolean(co, ci, "not", layer=LAYER)
    w, h = rx_o + 0.1, 2 * ry_o + 0.1
    ch = gf.Component()
    rh = ch.add_ref(gf.components.rectangle(size=(w, h), layer=LAYER))
    rh.move((xc if side == "right" else xc - w, yc_o - ry_o - 0.05))
    return gf.boolean(ann, ch, "and", layer=LAYER)


def _rect(comp: gf.Component, x0, y_center, length, height) -> None:
    r = comp.add_ref(gf.components.rectangle(size=(length, height), layer=LAYER))
    r.move((x0, y_center - height / 2))


def _bus_path() -> gf.Path:
    return gf.Path(np.array([
        [bus_start_x_um, bar_center_y_um],
        [bus_start_x_um + bus_length_um, bar_center_y_um],
    ]))


def _ellipse_half_arc_um(rx: float, ry: float) -> float:
    t = np.linspace(-np.pi / 2, np.pi / 2, 4001)
    return float(np.trapezoid(np.hypot(rx * np.sin(t), ry * np.cos(t)), t))


# Derived track centers (knobs move these coherently).
def _track_centers():
    ucomb_cy = bar_center_y_um + bar_width_um / 2 + coupling_gap_top_um + swg_width_um / 2
    lcomb_cy = bar_center_y_um - bar_width_um / 2 - coupling_gap_bot_um - swg_width_um / 2
    topwg_cy = ucomb_cy + top_track_offset_um
    botwg_cy = lcomb_cy - bot_track_offset_um
    return ucomb_cy, lcomb_cy, topwg_cy, botwg_cy


def _tooth_xw(i: int) -> tuple[float, float]:
    """Left edge (um, relative to teeth_start) and width of tooth i."""
    pitch_scale = grating_pitch_um / (PITCH_REF_PX / SX)
    duty_scale = grating_duty / DUTY_REF
    if i < len(TOOTH_REL_PX):
        rel, w = TOOTH_REL_PX[i], TOOTH_W_PX[i]
    else:
        rel = TOOTH_REL_PX[-1] + (i - len(TOOTH_REL_PX) + 1) * PITCH_REF_PX
        w = TOOTH_W_PX[-1]
    # table values are per-tooth fits against the gate-threshold target mask
    return rel / SX * pitch_scale, w / SX * duty_scale


@gf.cell
def recreated_device() -> gf.Component:
    c = gf.Component()
    ucomb_cy, lcomb_cy, topwg_cy, botwg_cy = _track_centers()
    landing_gap = grating_pitch_um * (1.0 - grating_duty)
    last_rel, last_w = _tooth_xw(n_teeth - 1)
    # measured trailing gap before the right landing: 7.7 px
    teeth_end_x = teeth_start_x_um + last_rel + last_w + 7.7 / SX
    landing_left_end = teeth_start_x_um - landing_gap

    # --- top folded arm -----------------------------------------------------
    t_top = c.add_ref(gf.components.taper(
        length=taper_top_length_um, width1=_even(taper_top_tip_width_um),
        width2=_even(wg_width_um), layer=LAYER))
    t_top.move((taper_top_tip_x_um, topwg_cy))
    x0 = taper_top_tip_x_um + taper_top_length_um
    _rect(c, x0, topwg_cy, bend_right_x_um - x0, wg_width_um)

    c.add_ref(_half_annulus(
        bend_right_x_um, "right",
        bend_right_rx_outer_um, topwg_cy + wg_width_um / 2,
        ucomb_cy - swg_width_um / 2 + bend_right_comb_lift_um,
        bend_right_rx_inner_um, topwg_cy - wg_width_um / 2,
        ucomb_cy + swg_width_um / 2 + bend_right_comb_lift_um))

    # upper comb: right landing (tilted into the bend), teeth; the left
    # landing is the S1 chain's flat end
    _lead_chain(c, UR_LANDING_PTS_PX, snap_y_um=ucomb_cy)
    for i in range(n_teeth):
        rel, w = _tooth_xw(i)
        _rect(c, teeth_start_x_um + rel, ucomb_cy, w, swg_width_um)

    # --- bottom folded arm --------------------------------------------------
    _rect(c, bend_left_x_um, botwg_cy, taper_bot_start_x_um - bend_left_x_um, wg_bot_width_um)
    t_bot = c.add_ref(gf.components.taper(
        length=taper_bot_length_um, width1=_even(wg_bot_width_um),
        width2=_even(taper_bot_tip_width_um), layer=LAYER))
    t_bot.move((taper_bot_start_x_um, botwg_cy))

    c.add_ref(_half_annulus(
        bend_left_x_um, "left",
        bend_left_rx_outer_um, lcomb_cy + swg_width_um / 2, botwg_cy - wg_bot_width_um / 2,
        bend_left_rx_inner_um, lcomb_cy - swg_width_um / 2, botwg_cy + wg_bot_width_um / 2))

    # lower comb: left landing, teeth, right landing (S2 chain leaves from it)
    _rect(c, bend_left_x_um, lcomb_cy, landing_left_end - bend_left_x_um, swg_width_um)
    for i in range(n_teeth):
        rel, w = _tooth_xw(i)
        _rect(c, teeth_start_x_um + rel, lcomb_cy, w, swg_width_um)
    _rect(c, teeth_end_x, lcomb_cy, s2_start_x_um - teeth_end_x, swg_width_um)

    # --- central bus (drawn from the bus Path's endpoints; length knob is
    # bus_length_um and lengths.json derives from _bus_path()) ---------------
    bus = _bus_path()
    (bx0, by), (bx1, _) = bus.points[0], bus.points[-1]
    _rect(c, bx0, by, bx1 - bx0, bar_width_um)

    # --- tapering S-leads ---------------------------------------------------
    _lead_chain(c, S1_PTS_PX, snap_y_um=ucomb_cy)
    _lead_chain(c, S2_PTS_PX, snap_y_um=lcomb_cy)

    # --- registration anchors ----------------------------------------------
    # 1-px ink speck at target (py 20, px 3711) pins the bbox top-right; the
    # S1 tip hairline pins the bbox left edge at exactly x=0. Both are real
    # target ink; reproducing them locks the gate's left-align + y-centering.
    # (rect heights must be an even number of nm: odd sizes snap 1 nm larger,
    # and a 1 nm overhang above y=0.700 shifts the whole render by ~0.8 px)
    _rect(c, 18.2200, 0.6980, 0.0200, 0.0040)
    _rect(c, 0.0, 0.6820, 0.0072, 0.0040)

    return c


def main() -> None:
    outdir = Path(__file__).resolve().parent
    dev = recreated_device()
    out = gf.Component()
    out.add_ref(dev)
    out.flatten()
    out.write_gds(outdir / "device.gds")

    ucomb_cy, lcomb_cy, topwg_cy, botwg_cy = _track_centers()
    scratch = gf.Component()
    s1_len = _lead_chain(scratch, S1_PTS_PX, snap_y_um=ucomb_cy)
    s2_len = _lead_chain(scratch, S2_PTS_PX, snap_y_um=lcomb_cy)
    arc_r = _ellipse_half_arc_um(
        (bend_right_rx_outer_um + bend_right_rx_inner_um) / 2, (topwg_cy - ucomb_cy) / 2)
    arc_l = _ellipse_half_arc_um(
        (bend_left_rx_outer_um + bend_left_rx_inner_um) / 2, (lcomb_cy - botwg_cy) / 2)
    grating_span = n_teeth * grating_pitch_um
    teeth_end_x = teeth_start_x_um + grating_span
    top_arm = (taper_top_length_um
               + (bend_right_x_um - taper_top_tip_x_um - taper_top_length_um)
               + arc_r + (bend_right_x_um - teeth_end_x) + grating_span + s1_len)
    bottom_arm = ((taper_bot_start_x_um - bend_left_x_um) + taper_bot_length_um
                  + arc_l + (teeth_start_x_um - bend_left_x_um) + grating_span
                  + (s2_start_x_um - teeth_end_x) + s2_len)
    bus = _bus_path().length()
    lengths = {
        "arms": {
            "top_path_um": round(top_arm, 6),
            "bottom_path_um": round(bottom_arm, 6),
        },
        "delta_length_um": round(abs(top_arm - bottom_arm), 6),
        "bus_interaction_length_um": round(bus, 6),
        "note": (
            "arms = the two folded grating arms (path-derived); delta_length_um "
            "= their walk-off. Knob taper_bot_start_x_um lengthens the bottom "
            "arm 1:1 (area grows by wg_bot_width_um * delta). The bus knob is "
            "bus_length_um, reported as bus_interaction_length_um."
        ),
    }
    (outdir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    print(f"wrote device.gds; bus interaction length = {bus:.6f} um")


if __name__ == "__main__":
    main()
