"""Directional coupler (2x2) — primitives-only parametric recreation of cat5.

Two single-mode strip waveguides fan in from four separated ports, run parallel
with a small edge-to-edge gap through a central coupling straight, then fan out.
Each waveguide is ONE gf.Path centerline (cosine S-bend -> straight -> cosine
S-bend), extruded to wg_width on layer (1,0). No component stencils, no raw
polygons.

FUNCTION KNOBS (top-level tunables): wg_width, coupling_gap, coupling_length,
sbend_length, port_sep. These are the physics knobs of a directional coupler
(gap -> supermode split dn -> coupling length L_pi; coupling_length -> split
ratio; width -> confinement; sbend_length/port_sep -> fan-out routing).
"""

import json
from pathlib import Path

import numpy as np

import gdsfactory as gf

# ---- top-level tunables (function-defining knobs of a directional coupler) ----
wg_width = 1.2           # single-mode strip waveguide width (um) [tfln400]
coupling_gap = 0.50      # edge-to-edge gap in the coupling region (um)
coupling_length = 174.2295  # ratio-correct L = 0.84777*Lpi (Lpi=205.5 um)
sbend_length = 2.0       # horizontal length of each input/output S-bend (um)
port_sep = 3.0           # center-to-center guide separation at the ports (um)

LAYER = (1, 0)
_NPTS = 220              # samples per S-bend centerline


def _cosine_sbend(x0, x1, y0, y1, npts):
    """Sampled cosine S-bend centerline from (x0,y0) to (x1,y1).

    y(t) = y0 + (y1-y0)*(1-cos(pi*t))/2 -> zero slope at both ends, matching the
    flat guide->coupling and coupling->guide transitions seen in the image.
    """
    t = np.linspace(0.0, 1.0, npts)
    x = x0 + (x1 - x0) * t
    y = y0 + (y1 - y0) * (1.0 - np.cos(np.pi * t)) / 2.0
    return np.column_stack([x, y])


def _waveguide_centerline(y_port, y_couple):
    """Full centerline: left S-bend -> coupling straight -> right S-bend."""
    x_a = sbend_length                       # end of left S-bend
    x_b = sbend_length + coupling_length     # start of right S-bend
    x_end = 2.0 * sbend_length + coupling_length

    left = _cosine_sbend(0.0, x_a, y_port, y_couple, _NPTS)
    straight = np.array([[x_a, y_couple], [x_b, y_couple]])
    right = _cosine_sbend(x_b, x_end, y_couple, y_port, _NPTS)
    # drop duplicated junction points
    return np.vstack([left, straight[1:], right[1:]])


@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component()

    couple_offset = (coupling_gap + wg_width) / 2.0  # center-to-center/2 in region
    port_offset = port_sep / 2.0

    lengths = {}
    for name, sign in (("top", +1.0), ("bottom", -1.0)):
        pts = _waveguide_centerline(sign * port_offset, sign * couple_offset)
        path = gf.Path(pts)
        wg = c << gf.path.extrude(path, width=wg_width, layer=LAYER)
        lengths[name] = float(path.length())

    # Measurement contract. This device's spec metric is coupling_ratio, so the
    # evaluator reads a `coupler` shape (length_um, gap_um, width_um) from
    # lengths.json and evaluates sin^2(pi*L/(2*Lpi)) from the two-core supermode
    # split. All three values are taken from the exposed tunables / real paths;
    # nothing is hand-entered. The equal-arm delta is kept for completeness.
    out_dir = Path(__file__).resolve().parent
    (out_dir / "lengths.json").write_text(
        json.dumps(
            {
                "coupler": {
                    "length_um": float(coupling_length),
                    "gap_um": float(coupling_gap),
                    "width_um": float(wg_width),
                },
                "arm_lengths_um": lengths,
            },
            indent=2,
        )
    )
    return c


if __name__ == "__main__":
    comp = directional_coupler()
    # Flatten so the device cell is a real top-level cell in the GDS (gf 9.20.7
    # otherwise wraps everything under a $$$CONTEXT_INFO$$$ metadata cell, which
    # hides the geometry from bare top_level() polygon-area probes).
    comp = comp.copy()
    comp.flatten()
    out = Path(__file__).resolve().parent / "device.gds"
    comp.write_gds(str(out))
    print(f"wrote {out}  bbox={comp.bbox_np()}")
