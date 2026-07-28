"""final8 — superlattice-clad dual-slab directional coupler (primitives only).

Two wide slab cores coupled through a central 5-wire lattice barrier, each core
clad on its outer side by a 5-line superlattice; all four corners feed the chip
edge via bent access bands. GDSFactory 9.20.7, layer (1, 0), device coords
x in [0, L_total], y in [-W_total/2, +W_total/2].
"""

import json
from pathlib import Path as FsPath

import gdsfactory as gf
import numpy as np

LAYER = (1, 0)

# ------------------------- tunables (top-level) -------------------------
L_total = 120.0
W_total = 4.0

# central lattice barrier (sets inter-core coupling)
n_center = 5
center_pitch = 0.1007
center_y0 = -0.00700
center_trims = [-0.00046, 0.00046, 0.0, 0.00106, -0.00044]  # drawn per-wire deviations
center_ys = [center_y0 + (n_center // 2 - i) * center_pitch + t for i, t in enumerate(center_trims)]
center_widths = [0.0700, 0.06850, 0.0600, 0.06450, 0.07056]

# slab cores
slab_width = 0.47084
slab_width_bot = 0.469
slab_y = 0.50130
slab_y_bot = 0.5025
coupling_length = 99.6  # straight interaction length — THE transfer-length knob
slab_center_x = 60.0

# outer superlattice cladding (index balance of the cores); outermost -> innermost
n_clad = 5
clad_y_top = [1.20170, 1.10150, 1.00158, 0.90206, 0.80086]
clad_w_top = [0.06716, 0.06800, 0.06716, 0.06800, 0.06716]
clad_y_bot = [1.20494, 1.10536, 1.00330, 0.90430, 0.80450]
clad_w_bot = [0.06576, 0.06716, 0.06716, 0.06716, 0.06800]
clad_xL = [7.82, 8.08, 8.37, 8.77, 9.44]
clad_xR = [112.07, 111.81, 111.49, 111.08, 110.45]

# slab corner feed: measured drawn centerline, x relative to the slab straight's
# left end (10.2 in the drawing), y absolute for the top half
FEED_PROFILE = [
    (-5.98, 2.40), (-5.82, 2.30), (-5.66, 2.20), (-5.50, 2.10), (-5.42, 2.05), (-5.34, 2.00), (-5.26, 1.95), (-5.18, 1.90), (-5.09, 1.85),
    (-5.00, 1.80), (-4.92, 1.75), (-4.83, 1.70), (-4.73, 1.65), (-4.64, 1.60),
    (-4.53, 1.55), (-4.42, 1.50), (-4.32, 1.45), (-4.19, 1.40), (-4.08, 1.35),
    (-3.96, 1.30), (-3.83, 1.25), (-3.80, 1.218), (-3.60, 1.141), (-3.40, 1.069),
    (-3.20, 1.003), (-3.00, 0.939), (-2.80, 0.879), (-2.60, 0.825), (-2.40, 0.781),
    (-2.20, 0.732), (-2.00, 0.690), (-1.80, 0.653), (-1.60, 0.619), (-1.40, 0.590),
    (-1.20, 0.564), (-1.00, 0.544), (-0.80, 0.528), (-0.60, 0.517), (-0.40, 0.509),
    (-0.20, 0.504), (0.00, 0.502), (0.20, 0.502), (0.40, 0.502),
]
feed_split1 = 8  # end of the wide exit section
feed_split2 = 24  # start of the taper to the slab width
feed_w_top = 0.70
feed_w_mid = 0.644
feed_w_flat = 0.47
feed_x_shift = -0.03

# cladding-bundle corner band: measured drawn centerline, absolute x, top half
BAND_PROFILE = [
    (6.61, 2.40), (6.75, 2.30), (6.89, 2.20), (7.03, 2.10), (7.14, 2.02), (7.19, 1.97), (7.25, 1.90), (7.34, 1.85), (7.41, 1.80),
    (7.50, 1.75), (7.59, 1.70), (7.67, 1.65), (7.77, 1.60), (7.87, 1.55),
    (7.98, 1.50), (8.12, 1.45), (8.24, 1.40), (8.38, 1.35), (8.57, 1.30),
    (8.85, 1.25), (9.08, 1.15), (9.27, 0.985), (9.53, 0.90), (9.88, 0.845),
    (10.03, 0.84),
]
band_split1 = 9  # end of the wide exit section
band_split2 = 15  # start of the taper to the tail
band_w_top = 0.70
band_w_mid = 0.644
band_w_tail = 0.24
band_x_shift = -0.03

# merge fillets where each cladding line tip meets the corner mass
fillet_len = 1.40
fillet_back = 0.12
fillet_w1 = 0.22
cap_len = 2.10
cap_w1 = 0.16
cap_offset = 0.058

# the drawn right-end curves sit slightly inward of a perfect mirror
right_curve_shift = 0.095


def _feed_pts(xl_slab):
    return np.array([(xl_slab + dx + feed_x_shift, y) for dx, y in FEED_PROFILE])


def _band_pts():
    return np.array([(x + band_x_shift, y) for x, y in BAND_PROFILE])


def _add_tapered_path(comp, pts, w_start, w_end):
    tr = gf.path.transition(
        gf.cross_section.cross_section(width=w_start, layer=LAYER),
        gf.cross_section.cross_section(width=w_end, layer=LAYER),
        width_type="linear",
    )
    comp.add_ref(gf.path.extrude_transition(gf.Path(pts), tr))


def _add_curve(comp, pts, split1, split2, w_top, w_mid, w_end, s, mirror_x, mirror_about):
    q = pts.copy()
    if mirror_x:
        q[:, 0] = 2 * mirror_about - q[:, 0] - right_curve_shift
    q = q * np.array([1.0, s])
    _add_tapered_path(comp, q[: split1 + 1], w_top, w_top)
    _add_tapered_path(comp, q[split1 : split2 + 1], w_mid, w_mid)
    _add_tapered_path(comp, q[split2:], w_mid, w_end)


def _rect(comp, x0, y_center, length, width):
    ref = comp.add_ref(gf.components.rectangle(size=(length, width), layer=LAYER))
    ref.move((x0, y_center - width / 2))


def _fillet(comp, x_tip, y_axis, rightward):
    """Taper wedge that fills the drawn merge between a line tip and the corner mass."""
    ref = comp.add_ref(
        gf.components.taper(length=fillet_len, width1=fillet_w1, width2=0.01, layer=LAYER)
    )
    if rightward:
        ref.move((x_tip - fillet_back, y_axis))
    else:
        ref.drotate(180)
        ref.move((x_tip + fillet_back, y_axis))


@gf.cell
def final8_device() -> gf.Component:
    asm = gf.Component()
    xl_slab = slab_center_x - coupling_length / 2

    for yc, w in zip(center_ys, center_widths):
        _rect(asm, 0.0, yc, L_total, w)

    for s in (+1.0, -1.0):  # top / bottom half
        clad_ys = clad_y_top if s > 0 else clad_y_bot
        clad_ws = clad_w_top if s > 0 else clad_w_bot
        sl_y = slab_y if s > 0 else slab_y_bot
        sl_w = slab_width if s > 0 else slab_width_bot

        _rect(asm, xl_slab, s * sl_y, coupling_length, sl_w)

        feed = _feed_pts(xl_slab)
        band = _band_pts()
        for mirror_x in (False, True):
            _add_curve(asm, feed, feed_split1, feed_split2, feed_w_top, feed_w_mid,
                       feed_w_flat, s, mirror_x, slab_center_x)
            _add_curve(asm, band, band_split1, band_split2, band_w_top, band_w_mid,
                       band_w_tail, s, mirror_x, L_total / 2)

        for k in range(n_clad):
            yk, wk = clad_ys[k], clad_ws[k]
            _rect(asm, clad_xL[k], s * yk, clad_xR[k] - clad_xL[k], wk)
            y_axis = s * (yk + wk / 2)
            _fillet(asm, clad_xL[k], y_axis, rightward=True)
            _fillet(asm, clad_xR[k], y_axis, rightward=False)

        cap_y = s * (clad_ys[0] + clad_ws[0] / 2 + cap_offset)
        for x_cap, rightward in ((clad_xL[0] + 0.40, True), (clad_xR[0] - 0.40, False)):
            ref = asm.add_ref(
                gf.components.taper(length=cap_len, width1=cap_w1, width2=0.01, layer=LAYER)
            )
            if not rightward:
                ref.drotate(180)
            ref.move((x_cap, cap_y))

    box = gf.Component()
    _rect(box, 0.0, 0.0, L_total, W_total)
    return gf.boolean(A=asm, B=box, operation="and", layer=LAYER)


if __name__ == "__main__":
    c = final8_device()

    xl = slab_center_x - coupling_length / 2
    xr = slab_center_x + coupling_length / 2
    straight = gf.Path(np.array([[xl, slab_y], [xr, slab_y]]))
    feed_len = gf.Path(_feed_pts(xl)).length()
    # the slab-core spine vs its bend-only portion: the difference is the
    # straight interaction length (the coupling_length knob), path-measured
    lengths = {
        "arms": {
            "slab_spine_um": straight.length() + 2 * feed_len,
            "slab_bends_um": 2 * feed_len,
        },
        "delta_length_um": straight.length(),
    }
    out_dir = FsPath(__file__).parent
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))

    c.write_gds(out_dir / "final8_superlattice_coupler.gds", with_metadata=False)
