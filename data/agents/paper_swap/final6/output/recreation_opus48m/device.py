"""Waveguide crossing (4-port low-loss tapered/lens crossing) — primitives only.

Two perpendicular single-mode waveguides, each locally widened into a biconvex
(elliptical) lens taper so the mode expands through the intersection and
re-narrows, giving low insertion loss / low crosstalk. The union of the two
orthogonal lens tapers plus the through-guides forms the 4-petal silhouette.

Recreated from experiments/paper_swap/final6/device_bw.png, footprint 4.7x4.7 um.
GDSFactory 9.20.7, layer (1, 0). Primitives only: gf.Path + extrude, taper,
straight, @gf.cell assembly. No gf.components device stencils, no raw polygons.
"""

import json
import math
from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

# --- Top-level tunables (function-defining knobs of a waveguide crossing) ---
wg_width = 0.236        # single-mode guide / port-stub width and lens tip width (um)
lens_len = 1.80         # half-length of the expansion petals along the axis (um)
lens_width = 0.90       # maximum full width of a petal (at its mid-radius) (um)
lens_center_width = 0.22  # petal width where the two guides cross at center (um)
lens_peak_frac = 0.45   # radial position of the petal's max width (fraction of lens_len)
arm_length_h = 4.7      # through-guide span of the horizontal waveguide (um)
arm_length_v = 4.7      # through-guide span of the vertical waveguide (um)
n_seg = 24              # taper segments approximating the elliptical petal edge


def _ellipse_lens(half_len: float, max_width: float, tip_width: float,
                  center_width: float, peak_frac: float, n: int) -> gf.Component:
    """The two collinear expansion petals of one crossing waveguide, along x in
    [-half_len, half_len]. Each petal is an elliptical lobe peaking at its
    mid-radius (|x| = half_len/2) and re-narrowing toward BOTH the crossing
    center (x=0 -> center_width) and its outer tip (|x|=half_len -> tip_width),
    which reproduces the concave cusps of a low-loss tapered crossing. Built
    from a chain of linear taper primitives (primitive only)."""
    c = gf.Component()
    dx = 2.0 * half_len / n
    r_peak = half_len * peak_frac

    def _snap(w: float) -> float:
        # widths must be a multiple of 0.002 um (2 dbu) in gdsfactory 9.20.7
        return round(w / 0.002) * 0.002

    def w_at(x: float) -> float:
        # elliptical lobe peaking at r_peak; inner half (center side) and outer
        # half (tip side) have their own semi-lengths so the peak can be shifted.
        if abs(x) < r_peak:
            d = (r_peak - abs(x)) / r_peak
            floor = center_width
        else:
            d = (abs(x) - r_peak) / max(1e-6, half_len - r_peak)
            floor = tip_width
        d = min(1.0, d)
        return _snap(max(floor, max_width * math.sqrt(max(0.0, 1.0 - d * d))))

    for i in range(n):
        xa = -half_len + i * dx
        xb = xa + dx
        wa = w_at(xa)
        wb = w_at(xb)
        seg = gf.components.taper(length=dx, width1=wa, width2=wb, layer=LAYER)
        ref = c.add_ref(seg)
        ref.move((xa, 0))
    return c


@gf.cell
def waveguide_crossing() -> gf.Component:
    c = gf.Component()

    # Through-guides (narrow straight waveguides spanning the full footprint;
    # their portions outside the lenses form the four port stubs).
    ph = gf.Path([(-arm_length_h / 2, 0.0), (arm_length_h / 2, 0.0)])
    pv = gf.Path([(0.0, -arm_length_v / 2), (0.0, arm_length_v / 2)])
    xs = gf.cross_section.cross_section(width=wg_width, layer=LAYER)
    c.add_ref(ph.extrude(xs))
    c.add_ref(pv.extrude(xs))

    # Orthogonal lens tapers (the mode-expansion petals).
    lens = _ellipse_lens(lens_len, lens_width, wg_width, lens_center_width,
                         lens_peak_frac, n_seg)
    c.add_ref(lens)                      # horizontal lens
    c.add_ref(lens).rotate(90)           # vertical lens

    # Self-measured arm lengths from the actual gf.Path objects (contract).
    lengths_path = Path(__file__).with_name("lengths.json")
    arms = {"horizontal": float(ph.length()), "vertical": float(pv.length())}
    payload = {"arms": arms,
               "delta_length_um": abs(arms["horizontal"] - arms["vertical"])}
    lengths_path.write_text(json.dumps(payload, indent=2))
    return c


if __name__ == "__main__":
    comp = waveguide_crossing()
    out = Path(__file__).with_name("device.gds")
    # with_metadata=False so the device cell is the top-level GDS cell (kfactory
    # otherwise nests it under a $$$CONTEXT_INFO$$$ cell, which the measurement
    # layer's top-level area scan skips).
    comp.write_gds(str(out), with_metadata=False)
    print("wrote", out)
