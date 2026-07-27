"""
2x2 directional coupler — primitives-only, parametric GDSFactory recreation.

Topology (see recreation_log.json): two single-mode waveguides enter separately,
S-bend into a parallel coupling region (small edge-to-edge gap over a coupling
length), then S-bend apart to two outputs. Symmetric top/bottom; the input and
output fan-outs differ slightly and the figure draws the access S-bends with a
widened (tapered) stroke, so the bend carries a parametric access-taper bulge.

All geometry is gf.Path + extrude on layer (1,0): straight leads, straight
coupling guides, and the S-bends as a sequence of short constant-width extrudes
whose width follows the access-taper profile. No gf.components device stencils,
no raw polygons. Centerlines are cosine S-bends and the reported arm lengths are
computed from the path objects themselves (lengths.json).
"""

import json
import math
from pathlib import Path

import numpy as np
import gdsfactory as gf

# ---- Top-level tunables (the parametric contract) -------------------------
# Function-defining knobs of a directional coupler:
coupling_gap = 0.141          # edge-to-edge gap in the parallel region (um)  [splitting knob]
coupling_length = 53.92       # length of the parallel coupling section (um)  [transfer length]
sbend_length = 15.476         # horizontal span of each access S-bend (um)
wg_width_top = 0.333          # top access/lead waveguide width (um)
wg_width_bot = 0.301          # bottom access/lead waveguide width (um)
coupling_width_top = 0.374    # top waveguide width in the coupling region (um)
coupling_width_bot = 0.259    # bottom waveguide width in the coupling region (um)
port_separation_in = 3.445    # center-to-center input port separation (um)
port_separation_out = 3.672   # center-to-center output port separation (um)
input_lead = 17.523           # input straight lead length (um)
# access-taper (the drawn S-bend stroke widening):
bend_taper_peak_top = 1.222   # peak width of the top S-bend taper (um)
bend_taper_peak_bot = 0.869   # peak width of the bottom S-bend taper (um)
bend_taper_center = 0.514     # fractional position of the taper peak along the bend
bend_taper_sigma_lead = 0.196     # taper spread on the lead side of the peak
bend_taper_sigma_coupling = 0.186  # taper spread on the coupling side of the peak

FOOTPRINT_LENGTH = 120.0      # total device length (um), from footprint.json
LAYER = (1, 0)
_BEND_SEGMENTS = 32           # short extrudes per S-bend (variable-width approximation)


def _grid(w: float) -> float:
    """Snap a width to the 2 nm symmetric-cross-section grid gdsfactory requires."""
    return max(0.002, round(w / 0.002) * 0.002)


def _coupling_offset() -> float:
    """Center-to-center half-separation of the two coupling guides (um)."""
    csep = coupling_gap + (coupling_width_top + coupling_width_bot) / 2.0
    return csep / 2.0


def _bend_width(t: float, w_lead: float, w_coup: float, peak: float,
                mu: float, sig_lead: float, sig_coup: float) -> float:
    """Access-taper width at fractional position t along the S-bend."""
    base = w_lead + (w_coup - w_lead) * t
    sig = sig_lead if t < mu else sig_coup
    return base + (peak - base) * math.exp(-((t - mu) / sig) ** 2)


def _add_sbend(c: gf.Component, xa: float, xb: float, ya: float, yb: float,
               w_a: float, w_b: float, peak: float, mu: float,
               sig_lead: float, sig_coup: float) -> gf.Path:
    """Cosine S-bend from (xa,ya)->(xb,yb) as short width-varying extrudes."""
    t = np.linspace(0.0, 1.0, _BEND_SEGMENTS + 1)
    shape = 0.5 * (1.0 - np.cos(math.pi * t))
    pts = np.column_stack([xa + (xb - xa) * t, ya + (yb - ya) * shape])
    for i in range(_BEND_SEGMENTS):
        tm = (i + 0.5) / _BEND_SEGMENTS
        wi = _grid(_bend_width(tm, w_a, w_b, peak, mu, sig_lead, sig_coup))
        seg = gf.Path(pts[i:i + 2])
        c.add_ref(gf.path.extrude(seg, gf.cross_section.cross_section(width=wi, layer=LAYER)))
    return gf.Path(pts)


def _add_straight(c: gf.Component, x0: float, x1: float, y: float, w: float) -> float:
    c.add_ref(gf.path.extrude(gf.Path([[x0, y], [x1, y]]),
                              gf.cross_section.cross_section(width=_grid(w), layer=LAYER)))
    return abs(x1 - x0)


@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component()
    output_lead = FOOTPRINT_LENGTH - input_lead - 2 * sbend_length - coupling_length
    cy_off = _coupling_offset()

    x1 = input_lead
    x2 = x1 + sbend_length
    x3 = x2 + coupling_length
    x4 = x3 + sbend_length
    x5 = x4 + output_lead

    arm_lengths = {}
    guides = [
        ("top", +1, wg_width_top, coupling_width_top, bend_taper_peak_top),
        ("bottom", -1, wg_width_bot, coupling_width_bot, bend_taper_peak_bot),
    ]
    for name, sgn, lw, cw, peak in guides:
        pin, cy, pout = sgn * port_separation_in / 2, sgn * cy_off, sgn * port_separation_out / 2
        length = 0.0
        length += _add_straight(c, 0.0, x1, pin, lw)
        length += _add_sbend(c, x1, x2, pin, cy, lw, cw, peak,
                             bend_taper_center, bend_taper_sigma_lead,
                             bend_taper_sigma_coupling).length()
        length += _add_straight(c, x2, x3, cy, cw)
        length += _add_sbend(c, x3, x4, cy, pout, cw, lw, peak,
                             1.0 - bend_taper_center, bend_taper_sigma_coupling,
                             bend_taper_sigma_lead).length()
        length += _add_straight(c, x4, x5, pout, lw)
        arm_lengths[name] = float(length)

    _write_lengths(arm_lengths["top"], arm_lengths["bottom"])
    return c


def _write_lengths(l_top: float, l_bot: float) -> None:
    """Measurement contract: the two guide centerline lengths + their difference."""
    out = {"arms": {"top": l_top, "bottom": l_bot},
           "delta_length_um": abs(l_top - l_bot)}
    (Path(__file__).parent / "lengths.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    comp = directional_coupler()
    # Flatten so the geometry cell is a real top-level cell in the GDS. Without
    # this, kfactory writes a $$$CONTEXT_INFO$$$ wrapper as the sole top cell,
    # which the (1,0)-layer readers in homi.spec_optimization skip -> 0 area.
    flat = comp.copy()
    flat.flatten()
    gds_path = Path(__file__).parent / "device.gds"
    flat.write_gds(str(gds_path))
    print(f"wrote {gds_path}")
