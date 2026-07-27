"""Directional coupler recreation -- final4 (primitives-only, parametric).

Topology: two identical single-mode strip waveguides. Each runs straight at its
port, S-bends toward the other, runs parallel across a central coupling region
(minimum edge-to-edge gap = coupling_gap), then S-bends apart and exits straight.
Power couples evanescently across the gap over the coupling region. The layout is
mirror-symmetric top/bottom (a balanced 2x2 directional coupler).

Primitives only: each waveguide is a gf.Path polyline (straight + cosine S-bend +
straight + cosine S-bend + straight) extruded to wg_width on layer (1, 0). No
gf.components device stencils, no raw polygons.
"""
import json
from pathlib import Path

import numpy as np
import gdsfactory as gf

# ---- Function-defining knobs (top-level tunables) --------------------------
wg_width = 0.66          # waveguide core width (um)  -> mode confinement, kappa
coupling_gap = 0.30      # edge-to-edge gap in coupling region (um) -> kappa
coupling_length = 3.0    # length of the parallel coupling region (um) -> power transfer
sbend_length = 6.5       # horizontal length of each S-bend approach (um) -> adiabaticity
bend_offset = 0.689      # vertical displacement of each S-bend (um) -> port fan-out
input_length = 1.0       # straight stub length at each port (um)

LAYER = (1, 0)
_OUT = Path(__file__).resolve().parent


def _cosine_sbend(x0: float, x1: float, y0: float, y1: float, n: int = 120) -> np.ndarray:
    """Smooth S-bend centerline; cosine profile -> zero slope at both ends (no kinks)."""
    x = np.linspace(x0, x1, n)
    u = (x - x0) / (x1 - x0)
    y = y0 + (y1 - y0) * (1.0 - np.cos(np.pi * u)) / 2.0
    return np.column_stack([x, y])


def _guide_points(y_far: float, y_near: float) -> np.ndarray:
    """One guide centerline: straight -> S-bend -> coupling straight -> S-bend -> straight."""
    x0 = 0.0
    x1 = x0 + input_length
    x2 = x1 + sbend_length
    x3 = x2 + coupling_length
    x4 = x3 + sbend_length
    x5 = x4 + input_length
    segs = [
        np.array([[x0, y_far], [x1, y_far]]),          # input straight
        _cosine_sbend(x1, x2, y_far, y_near)[1:],       # S-bend toward neighbor
        np.array([[x3, y_near]]),                       # coupling straight
        _cosine_sbend(x3, x4, y_near, y_far)[1:],       # S-bend away
        np.array([[x5, y_far]]),                        # output straight
    ]
    return np.vstack(segs)


@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component()
    y_near = (coupling_gap + wg_width) / 2.0   # half center-to-center at coupling region
    y_far = y_near + bend_offset               # half center-to-center at the ports

    top = gf.Path(_guide_points(+y_far, +y_near))
    bot = gf.Path(_guide_points(-y_far, -y_near))
    for path in (top, bot):
        c.add_ref(path.extrude(width=wg_width, layer=LAYER))

    # Measurement contract: the two guide path lengths (balanced coupler -> equal).
    lengths = {
        "arms": {"upper": float(top.length()), "lower": float(bot.length())},
    }
    lengths["delta_length_um"] = abs(lengths["arms"]["upper"] - lengths["arms"]["lower"])
    (_OUT / "lengths.json").write_text(json.dumps(lengths, indent=2))
    return c


if __name__ == "__main__":
    comp = directional_coupler()
    gds = _OUT / "device.gds"
    # with_metadata=False: keep the device cell top-level (no $$$CONTEXT_INFO$$$
    # wrapper), so gdstk-based measurement (_layer_area/_layer_bbox) sees the
    # (1, 0) polygons for knob verification and footprint checks.
    comp.write_gds(gds, with_metadata=False)
    print(f"wrote {gds}  bbox_um={comp.bbox_np().tolist()}")
