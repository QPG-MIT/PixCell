"""
Waveguide crossing (2 single-mode guides crossing at 90 deg), 4-fold symmetric.
Footprint target: 4.7 x 4.7 um, layer (1, 0).

Topology (measured from the target silhouette): each crossing arm is a
mode-expander that EXPANDS from the single-mode access width to a bulge peaking
at radius ~bulge_radius, then narrows to a WAIST at the crossing center. Two such
arms crossed orthogonally give the four-lobed "clover": the four bulges are the
lobes, the diagonal notches are where neither arm has material, and the crossed
waists fill the center. Four single-mode rectangle stubs feed the ports.

Built with primitives only: each arm is a chain of `taper` primitives following
the measured width profile; stubs are rectangles.

Recreation target: experiments/paper_swap/final6/device_bw.png
"""

import json
from pathlib import Path

import numpy as np
import gdsfactory as gf

# ---- Tunables (top-level; the crossing's function knobs) ----
wg_width = 0.24          # single-mode access / arm-tip width [um]                 (PRIMARY)
lens_length = 3.40       # mode-expander length per arm, tip-to-tip [um]           (PRIMARY optical)
lens_max_width = 0.89    # peak bulge width (max mode expansion) [um]              (PRIMARY optical)
waist_width = 0.66       # arm width at the crossing center (the waist) [um]       (controls center fill / crosstalk)
bulge_radius = 0.90      # radius from center where each arm's bulge peaks [um]    (bulge position)
stub_length = 0.65       # single-mode access stub length per side [um]
arm_delta_length = 0.0   # horizontal/vertical arm-length asymmetry [um] (0 = symmetric crossing)
n_seg = 44               # taper segments per arm (silhouette smoothness; not an optical knob)
LAYER = (1, 0)

_DBU = 0.002             # grid: taper port widths must be a multiple of 2 DBU


def _snap(w: float) -> float:
    return max(_DBU, round(w / _DBU) * _DBU)


def _arm_fullwidth(x: float, w_tip: float, w_peak: float, w_waist: float,
                   half_len: float, r_peak: float) -> float:
    """Full arm width at longitudinal position x (center at 0). Elliptical bulge:
    w_waist at x=0, rising to w_peak at |x|=r_peak, falling to w_tip at |x|=half_len."""
    r = abs(x)
    if r >= half_len:
        return w_tip
    if r >= r_peak:                                   # outer flank: (r_peak,w_peak)->(half_len,w_tip)
        f = (r - r_peak) / (half_len - r_peak)
        s = float(np.sqrt(max(0.0, 1.0 - f * f)))
        return w_tip + (w_peak - w_tip) * s
    # inner flank: (r_peak,w_peak)->(0,w_waist), elliptical, ends at w_waist (not w_tip)
    s0 = (w_waist - w_tip) / (w_peak - w_tip)         # shape value at x=0
    f = (r_peak - r) / r_peak
    s = float(np.sqrt(max(0.0, 1.0 - (1.0 - s0 * s0) * f * f)))
    return w_tip + (w_peak - w_tip) * s


@gf.cell
def arm(lens_length: float = lens_length, wg_width: float = wg_width,
        lens_max_width: float = lens_max_width, waist_width: float = waist_width,
        bulge_radius: float = bulge_radius, n: int = n_seg) -> gf.Component:
    """One mode-expander arm (tip -> bulge -> waist -> bulge -> tip), long axis x,
    centered on the origin. Chain of `taper` primitives following the bulge profile."""
    c = gf.Component()
    half = lens_length / 2.0
    dx = lens_length / n
    for i in range(n):
        x1 = -half + i * dx
        x2 = -half + (i + 1) * dx
        w1 = _snap(_arm_fullwidth(x1, wg_width, lens_max_width, waist_width, half, bulge_radius))
        w2 = _snap(_arm_fullwidth(x2, wg_width, lens_max_width, waist_width, half, bulge_radius))
        seg = gf.components.taper(length=dx, width1=w1, width2=w2, layer=LAYER)
        ref = c << seg
        ref.movex(x1)                                 # taper spans x:0->dx, y-centered
    return c


@gf.cell
def crossing(wg_width: float = wg_width, lens_length: float = lens_length,
             lens_max_width: float = lens_max_width, waist_width: float = waist_width,
             bulge_radius: float = bulge_radius, stub_length: float = stub_length,
             arm_delta_length: float = arm_delta_length) -> gf.Component:
    """90-degree waveguide crossing: two orthogonal bulge-arms (union) fed by four
    single-mode rectangle stubs at N/S/E/W."""
    c = gf.Component()
    L = lens_length

    body = arm(lens_length=L, wg_width=wg_width, lens_max_width=lens_max_width,
               waist_width=waist_width, bulge_radius=bulge_radius, n=n_seg)
    c << body                                         # horizontal arm
    va = c << body
    va.rotate(90)                                     # vertical arm

    # four single-mode access stubs (rectangles), continuous with the arm tips
    r = c << gf.components.rectangle(size=(stub_length, wg_width), layer=LAYER)
    r.movex(L / 2); r.movey(-wg_width / 2)                              # right (+x)
    l = c << gf.components.rectangle(size=(stub_length, wg_width), layer=LAYER)
    l.movex(-L / 2 - stub_length); l.movey(-wg_width / 2)               # left (-x)
    b = c << gf.components.rectangle(size=(wg_width, stub_length), layer=LAYER)
    b.movex(-wg_width / 2); b.movey(-L / 2 - stub_length)               # bottom (-y)
    t = c << gf.components.rectangle(size=(wg_width, stub_length + arm_delta_length), layer=LAYER)
    t.movex(-wg_width / 2); t.movey(L / 2)                              # top (+y), + asymmetry knob

    return c


if __name__ == "__main__":
    c = crossing()
    out_dir = Path(__file__).resolve().parent
    gds_path = out_dir / "device.gds"
    # with_metadata=False: keep the geometry as the top-level GDS cell. kfactory's
    # default writes a $$$CONTEXT_INFO$$$ parent cell that the measurement helpers
    # (_layer_area / measured_delta_length -> library.top_level(), skip "$$$")
    # would otherwise read as empty.
    c.write_gds(str(gds_path), with_metadata=False)

    # lengths.json (measurement contract): the two crossing arms, tip-to-tip,
    # derived from the actual component bounding box (x-extent = horizontal arm,
    # y-extent = vertical arm), never hand-entered.
    bb = c.dbbox()
    Lh = round(bb.width(), 6)
    Lv = round(bb.height(), 6)
    lengths = {
        "arms": {"horizontal": Lh, "vertical": Lv},
        "delta_length_um": round(abs(Lv - Lh), 6),
    }
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))

    print(f"wrote {gds_path}")
    print(f"bbox_um = {Lh} x {Lv}   delta_length_um = {lengths['delta_length_um']}")
