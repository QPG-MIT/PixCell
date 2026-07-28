"""final7 Phase-A recreation: loop-embedded dual-arm interferometer.

A closed stadium loop (rounded-rectangle ring; elliptical corners in um space
because the calibrated axes are anisotropic: 3.0 um across x, 5.5 um across y)
whose left/right inner walls launch hub stubs that Y-split into two parallel
horizontal arm guides; each arm carries a two-window slotted loading rail on
its outer side. Catalog primitives only: rectangle, ellipse, gf.Path+extrude,
boolean. Layer (1, 0). gdsfactory 9.20.7.

Edge convention: the raster gate inks the polygon boundary line, so every
black edge that faces white on its low-y or high-x side carries a half-pixel
bias (EBY / EBX) pulling it into the black; measured from the 245-threshold
target mask at 517.0 x 141.818 px/um.
"""
import json
from pathlib import Path

import numpy as np
import gdsfactory as gf

LAYER = (1, 0)

# ---------------- function knobs (um) ----------------
delta_length = 0.0      # top-minus-bottom arm path imbalance (interferometer knob)
arm_length = 0.89072    # straight arm (interaction) length
arm_pitch = 1.03125     # arm center-to-center separation
wg_width = 0.24680      # top arm guide width
wg_width_bot = 0.23622  # bottom arm guide width

# ---------------- raster edge bias (um) ----------------
EBX = 0.000967          # half-pixel in x
EBY = 0.003526          # half-pixel in y

# ---------------- loop (ring) knobs (um) ----------------
ring_length = 3.0
ring_height = 5.5
ring_x1 = 2.99903       # outer right edge (bias applied)
ring_y0 = 0.00353       # outer bottom edge (bias applied)
# per-corner outer ellipse radii (rx, ry), area-weighted fits
ring_r_ul = (0.9207, 2.5667)
ring_r_ur = (0.9207, 2.5949)
ring_r_ll = (0.9130, 2.5667)
ring_r_lr = (0.9168, 2.5808)
inner_x0 = 0.31044
inner_x1 = 2.68472
inner_y0 = 0.53590
inner_y1 = 4.98173
inner_r_ul = (0.7157, 1.7487)
inner_r_ur = (0.7118, 1.7628)
inner_r_ll = (0.6963, 1.7346)
inner_r_lr = (0.7002, 1.7346)

# ---------------- arm / loading structure (um) ----------------
bar_x0 = 1.05222
core_axis_y = 2.74560   # arm-pair mirror axis
rail_top_y = 4.18141    # top rail outer edge
rail_bot_y = 1.30801    # bottom rail outer edge (bias applied)
# window cut rectangles [x0, x1, y0, y1] (bias applied on left/top edges)
win_tl = (1.11509, 1.44487, 3.38462, 3.93109)
win_tr = (1.55416, 1.88008, 3.38462, 3.93109)
win_bl_a = (1.11702, 1.23598, 1.55129, 2.11186)  # ragged bottom edge: left part row 574
win_bl_b = (1.23598, 1.44487, 1.55834, 2.11186)  # right part row 573
win_br = (1.55416, 1.88008, 1.55834, 2.11186)

# ---------------- hub / branch / Y-junction (um) ----------------
hub_x_inner = 0.20      # tucked into the ring wall
hub_x_tip = 0.51934     # hub right edge (bias applied)
hub_y0 = 2.09776        # (bias applied)
hub_y1 = 3.40577
branch_v = 0.43366      # horizontal band thickness (243..305 rows, bias applied)
branch_c_top = 3.66843  # band center: [3.45160, 3.88526]
branch_x_bend = 0.7524
branch_x_end = 1.13     # fuses into the box; window cut trims it
diag_x0 = 0.47
diag_x1 = 0.76
diag_slope = 2.188
diag_w = 0.214
diag_anchor_y = 3.1135  # top-left diagonal centerline y at diag_x0
diag_mirror_y = 2.7465  # measured mirror axis of the diagonals
core_mirror_x = 1.49807
core_y_mid = 2.75       # hub / branch mirror axis

# ---------------- boundary micro-patches (um) ----------------
# The target's ring boundary is slightly superelliptical; these thin rects
# staircase the residual crescents at the flat<->corner transitions and the
# inner-wall flats (net-gain-positive against the measured mask).
# Each entry: (x0, y0, x1, y1).
cut_patches = (
    (0.77369, 0.00176, 0.89555, 0.03702),
    (0.69439, 0.03702, 0.78143, 0.07933),
    (0.89555, 0.00176, 0.96712, 0.01587),
    (0.63636, 0.07933, 0.69246, 0.12869),
    (2.10445, 0.00176, 2.22244, 0.03702),
    (2.22050, 0.03702, 2.30174, 0.07933),
    (2.03482, 0.00176, 2.10445, 0.01587),
    (2.31141, 0.08638, 2.35977, 0.12869),
    (0.78143, 5.46651, 0.88395, 5.51587),
    (0.70019, 5.42420, 0.77563, 5.51587),
    (0.88395, 5.48766, 0.95358, 5.51587),
    (2.11605, 5.46651, 2.21470, 5.51587),
    (2.04255, 5.48766, 2.11605, 5.51587),
    (2.22437, 5.42420, 2.29981, 5.51587),
    (2.67118, 3.40753, 2.68472, 3.55561),
    (2.67118, 1.93382, 2.68472, 2.09600),
    (2.44487, 2.96330, 2.46615, 3.01971),
    (0.52805, 2.96330, 0.55319, 3.01266),
)
add_patches = (
    (1.84333, 4.96587, 2.04836, 4.99407),
    (2.02708, 4.95176, 2.08317, 4.99407),
    (0.95164, 4.96587, 1.08124, 4.99407),
    (0.91296, 4.95176, 0.96905, 4.99407),
)


def _rect(comp: gf.Component, x0: float, y0: float, x1: float, y1: float) -> None:
    # snap to the 1 nm dbu grid BEFORE sizing so abutting rects share edges
    # exactly (position+size rounding desync leaves 1 nm slivers otherwise)
    xa, xb = sorted((round(x0, 3), round(x1, 3)))
    ya, yb = sorted((round(y0, 3), round(y1, 3)))
    ref = comp.add_ref(gf.components.rectangle(size=(xb - xa, yb - ya), layer=LAYER))
    ref.dmove((xa, ya))


def _stadium4(x0: float, y0: float, x1: float, y1: float,
              r_ul: tuple, r_ur: tuple, r_ll: tuple, r_lr: tuple) -> gf.Component:
    """Filled rounded rectangle with per-corner elliptical radii."""
    comp = gf.Component()
    for (rx, ry), cx, cy in (
        (r_ul, x0 + r_ul[0], y1 - r_ul[1]),
        (r_ur, x1 - r_ur[0], y1 - r_ur[1]),
        (r_ll, x0 + r_ll[0], y0 + r_ll[1]),
        (r_lr, x1 - r_lr[0], y0 + r_lr[1]),
    ):
        ref = comp.add_ref(gf.components.ellipse(radii=(rx, ry), layer=LAYER))
        ref.dmove((cx, cy))
    # center bands
    _rect(comp, x0 + max(r_ul[0], r_ll[0]), y0, x1 - max(r_ur[0], r_lr[0]), y1)
    _rect(comp, x0, y0 + max(r_ll[1], r_lr[1]), x1, y1 - max(r_ul[1], r_ur[1]))
    # edge strips (cover flats between unequal corners)
    _rect(comp, x0 + r_ul[0], y1 - min(r_ul[1], r_ur[1]), x1 - r_ur[0], y1)
    _rect(comp, x0 + r_ll[0], y0, x1 - r_lr[0], y0 + min(r_ll[1], r_lr[1]))
    _rect(comp, x0, y0 + r_ll[1], x0 + min(r_ul[0], r_ll[0]), y1 - r_ul[1])
    _rect(comp, x1 - min(r_ur[0], r_lr[0]), y0 + r_lr[1], x1, y1 - r_ur[1])
    return comp


def build() -> gf.Component:
    solid = gf.Component()

    outer = _stadium4(0.0, ring_y0, ring_x1, ring_height,
                      ring_r_ul, ring_r_ur, ring_r_ll, ring_r_lr)
    inner = _stadium4(inner_x0, inner_y0, inner_x1, inner_y1,
                      inner_r_ul, inner_r_ur, inner_r_ll, inner_r_lr)
    ring = gf.boolean(outer, inner, operation="not", layer=LAYER)
    solid.add_ref(ring)

    def mx(x: float) -> float:
        return 2.0 * core_mirror_x - x

    bar_x1 = bar_x0 + arm_length
    top_bar_c = core_axis_y + arm_pitch / 2.0
    bot_bar_c = core_axis_y - arm_pitch / 2.0
    branch_c_bot = 2.0 * core_y_mid - branch_c_top
    diag_xm = branch_x_bend - 0.0296  # centerline crosses the band center here
    diag_y1 = branch_c_top + diag_slope * (diag_x1 - diag_xm)

    for flip in (False, True):  # left half, right half
        def fx(x: float) -> float:
            return mx(x) if flip else x

        # hub slab (tucks into the ring wall)
        _rect(solid, fx(hub_x_inner), hub_y0, fx(hub_x_tip), hub_y1)
        # horizontal branch bands (bias already in branch_c/branch_v constants;
        # the y-mirror flips the bias, so the bottom band restores +EBY)
        _rect(solid, fx(branch_x_bend), branch_c_top - branch_v / 2.0,
              fx(branch_x_end), branch_c_top + branch_v / 2.0)
        _rect(solid, fx(branch_x_bend), branch_c_bot - branch_v / 2.0 + EBY,
              fx(branch_x_end), branch_c_bot + branch_v / 2.0 + EBY)
        # Y-junction diagonals (extruded 2-point paths)
        up_p = gf.Path(np.array([[fx(diag_x0), diag_anchor_y],
                                 [fx(diag_x1), diag_y1]]))
        dn_p = gf.Path(np.array([
            [fx(diag_x0), 2.0 * diag_mirror_y - diag_anchor_y],
            [fx(diag_x1), 2.0 * diag_mirror_y - diag_y1],
        ]))
        solid.add_ref(up_p.extrude(width=diag_w, layer=LAYER))
        solid.add_ref(dn_p.extrude(width=diag_w, layer=LAYER))
        # elbow fillet patches (outer corner of the diagonal -> band bends)
        _rect(solid, fx(0.680), 3.780, fx(branch_x_bend), 3.830)
        _rect(solid, fx(0.712), 3.830, fx(branch_x_bend), 3.88526)
        _rect(solid, fx(0.680), 1.670, fx(branch_x_bend), 1.720)
        _rect(solid, fx(0.712), 1.61827, fx(branch_x_bend), 1.670)
        # hub-tip fillet patches (diagonal roots)
        _rect(solid, fx(0.510), 2.966, fx(0.551), 3.086)
        _rect(solid, fx(0.510), 2.414, fx(0.551), 2.522)

    # arm guides (top bar carries the delta_length imbalance)
    _rect(solid, bar_x0, top_bar_c - wg_width / 2.0 + EBY,
          bar_x1 + delta_length, top_bar_c + wg_width / 2.0)
    _rect(solid, bar_x0, bot_bar_c - wg_width_bot / 2.0,
          bar_x1, bot_bar_c + wg_width_bot / 2.0)

    # loading boxes: solid rail+post blocks above/below the bars
    _rect(solid, bar_x0, top_bar_c + wg_width / 2.0, bar_x1, rail_top_y)
    _rect(solid, bar_x0, rail_bot_y, bar_x1, bot_bar_c - wg_width_bot / 2.0)

    # boundary micro-patch additions
    for x0, y0, x1, y1 in add_patches:
        _rect(solid, x0, y0, x1, y1)

    # windows carved out of the boxes + boundary micro-patch cuts
    cuts = gf.Component()
    for x0, x1, y0, y1 in (win_tl, win_tr, win_bl_a, win_bl_b, win_br):
        _rect(cuts, x0, y0, x1, y1)
    for x0, y0, x1, y1 in cut_patches:
        _rect(cuts, x0, y0, x1, y1)

    return gf.boolean(solid, cuts, operation="not", layer=LAYER)


def arm_paths() -> tuple[gf.Path, gf.Path]:
    """Arm centerlines (hub tip -> Y -> arm -> Y -> hub tip), top carries delta."""
    def mxp(x: float) -> float:
        return 2.0 * core_mirror_x - x

    post_cx = bar_x0 + 0.032
    top_bar_c = core_axis_y + arm_pitch / 2.0
    bot_bar_c = core_axis_y - arm_pitch / 2.0
    branch_c_bot = 2.0 * core_y_mid - branch_c_top
    diag_xm = branch_x_bend - 0.0296
    tip_y_top = branch_c_top - diag_slope * (diag_xm - diag_x0)

    def polyline(branch_c: float, bar_c: float, tip_y: float, extra: float) -> gf.Path:
        pts = [
            (diag_x0, tip_y),
            (diag_xm, branch_c),
            (post_cx, branch_c),
            (post_cx, bar_c),
            (mxp(post_cx) + extra, bar_c),
            (mxp(diag_xm) + extra, branch_c),
            (mxp(diag_x0) + extra, tip_y),
        ]
        return gf.Path(np.array(pts))

    top = polyline(branch_c_top, top_bar_c, tip_y_top, delta_length)
    bottom = polyline(branch_c_bot, bot_bar_c,
                      2.0 * diag_mirror_y - tip_y_top, 0.0)
    return top, bottom


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    component = build()
    component.write_gds(out_dir / "final7_recreated.gds")

    top, bottom = arm_paths()
    lengths = {
        "arms": {"top_um": float(top.length()), "bottom_um": float(bottom.length())},
        "delta_length_um": float(top.length() - bottom.length()),
    }
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    print(f"wrote final7_recreated.gds; delta_length_um={lengths['delta_length_um']:.6f}")
