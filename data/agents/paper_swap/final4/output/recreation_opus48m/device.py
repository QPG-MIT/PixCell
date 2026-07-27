"""Symmetric 2x2 directional coupler, primitives-only parametric build.

Two single-mode guides: straight leads -> raised-cosine S-bends in -> a short
straight coupling region at a small gap -> S-bends out -> straight leads. Built
entirely from gf.Path centerlines + extrude (a primitive), layer (1,0).
"""

import json
import math
from pathlib import Path

import gdsfactory as gf

# ---- Top-level tunables (parametric contract; FUNCTION knobs of the coupler) ----
total_length = 18.0        # overall device length (um)
wg_width = 0.65            # single-mode waveguide width (um)
port_separation = 2.34     # center-to-center guide separation at the ports (um)
coupling_gap = 0.37        # edge-to-edge gap in the coupling region (um) -- dominant coupler knob
coupling_length = 3.0      # straight parallel coupling length (um) -- sets split ratio
bend_length = 6.5          # each S-bend access transition length (um)
straight_length = 1.0      # straight lead at each port (um)
layer = (1, 0)
_n_pts = 120               # samples per S-bend centerline


def _sbend_points(x0, y0, x1, y1, n):
    """Raised-cosine S-bend centerline points from (x0,y0) to (x1,y1)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * (1.0 - math.cos(math.pi * t)) / 2.0
        pts.append((x, y))
    return pts


def _arm_points(y_port, y_couple):
    """Full centerline of one arm, left port -> right port, at the given offsets."""
    xa = straight_length
    xb = xa + bend_length
    xc = xb + coupling_length
    xd = xc + bend_length
    xe = xd + straight_length  # == total_length
    pts = [(0.0, y_port)]
    pts += _sbend_points(xa, y_port, xb, y_couple, _n_pts)[1:]
    pts += [(xc, y_couple)]
    pts += _sbend_points(xc, y_couple, xd, y_port, _n_pts)[1:]
    pts += [(xe, y_port)]
    return pts


@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component()
    y_port = port_separation / 2.0
    y_couple = (coupling_gap + wg_width) / 2.0

    top_pts = _arm_points(+y_port, +y_couple)
    bot_pts = _arm_points(-y_port, -y_couple)

    top_path = gf.Path(top_pts)
    bot_path = gf.Path(bot_pts)
    c << gf.path.extrude(top_path, width=wg_width, layer=layer)
    c << gf.path.extrude(bot_path, width=wg_width, layer=layer)

    # Measurement contract: write arm centerline lengths for the evaluator.
    lengths = {"top": float(top_path.length()), "bottom": float(bot_path.length())}
    delta = abs(lengths["top"] - lengths["bottom"])
    out = Path(__file__).parent / "lengths.json"
    out.write_text(json.dumps({"arms": lengths, "delta_length_um": delta}, indent=2))
    return c


if __name__ == "__main__":
    comp = directional_coupler()
    # with_metadata=False: keep directional_coupler as the true top-level cell
    # (kfactory's $$$CONTEXT_INFO$$$ wrapper otherwise hides it from area/bbox checks).
    comp.write_gds(Path(__file__).parent / "device.gds", with_metadata=False)
    print("wrote device.gds", comp.size_info.width, comp.size_info.height)
