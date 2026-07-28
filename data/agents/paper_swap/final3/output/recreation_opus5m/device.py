"""Symmetric 2x2 evanescent directional coupler — primitives-only parametric build.

Topology: two identical single-mode waveguides, mirror images about y = 0.
Each runs   straight -> S-bend in -> parallel coupling section -> S-bend out -> straight.
The two parallel sections are separated by `coupling_gap`, which is where the
evanescent field overlap lives; `coupling_length` sets the accumulated coupling
phase kappa*L and therefore the splitting ratio.

Only primitives are used: gf.Path centrelines + extrude through a
gf.cross_section. No gf.components device stencils, no raw polygons.
"""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np

# --------------------------------------------------------------------------
# Tunables (top-level `name = value`, JEE-substitutable).
# The function knobs of a directional coupler are the first four.
# --------------------------------------------------------------------------
coupling_length = 55.383       # um  interaction length of the parallel section
coupling_gap = 0.1615         # um  edge-to-edge gap in the parallel section
wg_width = 0.304             # um  waveguide width (both guides, uniform)
sbend_in_length = 13.529       # um  x-run of the input S-bends
sbend_in_offset = 1.5013      # um  y-rise of the input S-bends (per guide)
sbend_out_length = 14.383      # um  x-run of the output S-bends
sbend_out_offset = 1.5967     # um  y-rise of the output S-bends (per guide)
input_straight_length = 18.209   # um  input port stub
output_straight_length = 18.114  # um  output port stub

layer_num = 1
layer_dtype = 0

n_bend_points = 241           # discretisation of each S-bend centreline


def _sbend_points(dx: float, dy: float, n: int = n_bend_points) -> np.ndarray:
    """Raised-cosine S-bend centreline from (0, 0) to (dx, dy).

    y(t) = dy * (1 - cos(pi t)) / 2 has zero slope at both ends, so the bend
    joins the adjacent straights with continuous tangent (no kink, no
    radiation from an abrupt direction change).
    """
    t = np.linspace(0.0, 1.0, n)
    return np.column_stack([dx * t, dy * (1.0 - np.cos(np.pi * t)) / 2.0])


def _arm_points(sign: int) -> np.ndarray:
    """Centreline of one guide. sign=+1 is the upper guide, -1 the lower."""
    y_coup = sign * (coupling_gap + wg_width) / 2.0
    y_in = y_coup + sign * sbend_in_offset
    y_out = y_coup + sign * sbend_out_offset

    x = 0.0
    segments = [np.array([[x, y_in], [x + input_straight_length, y_in]])]
    x += input_straight_length

    segments.append(_sbend_points(sbend_in_length, y_coup - y_in) + [x, y_in])
    x += sbend_in_length

    segments.append(np.array([[x, y_coup], [x + coupling_length, y_coup]]))
    x += coupling_length

    segments.append(_sbend_points(sbend_out_length, y_out - y_coup) + [x, y_coup])
    x += sbend_out_length

    segments.append(np.array([[x, y_out], [x + output_straight_length, y_out]]))

    pts = np.vstack(segments)
    keep = np.ones(len(pts), dtype=bool)
    keep[1:] = np.any(np.abs(np.diff(pts, axis=0)) > 1e-9, axis=1)
    return pts[keep]


@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component()
    xs = gf.cross_section.cross_section(
        width=wg_width, layer=(layer_num, layer_dtype)
    )
    for sign in (+1, -1):
        path = gf.Path(_arm_points(sign))
        c.add_ref(path.extrude(xs))
    return c


def _arm_lengths() -> dict[str, float]:
    """Centreline path lengths measured from the gf.Path objects themselves."""
    return {
        "top_waveguide": float(gf.Path(_arm_points(+1)).length()),
        "bottom_waveguide": float(gf.Path(_arm_points(-1)).length()),
    }


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    component = directional_coupler()
    gds_path = out_dir / "device.gds"
    # with_metadata=False keeps kfactory's $$$CONTEXT_INFO$$$ cell out of the
    # file; that cell otherwise becomes the only GDS top cell and hides the
    # geometry from area-measuring readers (gdstk top_level()).
    component.write_gds(gds_path, with_metadata=False)

    arms = _arm_lengths()
    lengths = list(arms.values())
    (out_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": arms,
                "delta_length_um": abs(lengths[0] - lengths[1]),
                "coupling_length_um": float(coupling_length),
                "coupling_gap_um": float(coupling_gap),
                "wg_width_um": float(wg_width),
            },
            indent=2,
        )
    )
    print(f"wrote {gds_path}")
    print(f"bbox um: {component.dbbox()}")
    print(f"arms: {arms}")
