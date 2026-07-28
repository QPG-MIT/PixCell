"""Symmetric directional coupler — primitives-only parametric recreation.

Two mirror-symmetric waveguides: straight in, raised-cosine S-bend to a
close-gap parallel coupling section, S-bend back out. Built exclusively from
gf.Path centerlines + extrude (no component stencils, no raw polygons).
"""

import json
from pathlib import Path

import numpy as np
import gdsfactory as gf

# --- function-defining tunables (um) ---
wg_width_um = 0.666      # guide width (mode confinement); grid: multiple of 0.002
gap_um = 0.30            # edge-to-edge gap in the coupling region
coupling_len_um = 0.8    # length of the close-parallel coupling section
sbend_len_um = 8.6       # S-bend length (adiabaticity / residual coupling)
straight_in_um = 0.0     # straight lead at each port
io_sep_um = 2.342        # input/output port center-to-center separation

LAYER = (1, 0)
_N = 400  # samples per S-bend


def _sbend_pts(x0, y0, dx, dy):
    t = np.linspace(0.0, 1.0, _N)
    xs = x0 + dx * t
    ys = y0 + dy * (t - np.sin(2.0 * np.pi * t) / (2.0 * np.pi))
    return np.column_stack([xs, ys])


def _dedupe(pts):
    keep = np.ones(len(pts), bool)
    keep[1:] = np.linalg.norm(np.diff(pts, axis=0), axis=1) > 1e-9
    return pts[keep]


@gf.cell
def directional_coupler():
    c = gf.Component()
    total_len = 2 * straight_in_um + 2 * sbend_len_um + coupling_len_um
    x_c0 = straight_in_um + sbend_len_um
    for sign in (+1, -1):
        y_io = sign * io_sep_um / 2.0
        y_c = sign * (gap_um + wg_width_um) / 2.0
        left = np.vstack(
            [
                [(0.0, y_io), (straight_in_um, y_io)],
                _sbend_pts(straight_in_um, y_io, sbend_len_um, y_c - y_io),
            ]
        )
        coup = np.array([(x_c0, y_c), (x_c0 + coupling_len_um, y_c)])
        right = left[::-1].copy()
        right[:, 0] = total_len - right[:, 0]
        pts = _dedupe(np.vstack([left, coup, right]))
        c.add_ref(gf.path.extrude(gf.Path(pts), width=wg_width_um, layer=LAYER))
    return c


def _measure_lengths():
    """Arm lengths from the path objects themselves (measurement contract)."""
    y_io = io_sep_um / 2.0
    y_c = (gap_um + wg_width_um) / 2.0
    left = np.vstack(
        [
            [(0.0, y_io), (straight_in_um, y_io)],
            _sbend_pts(straight_in_um, y_io, sbend_len_um, y_c - y_io),
        ]
    )
    total_len = 2 * straight_in_um + 2 * sbend_len_um + coupling_len_um
    x_c0 = straight_in_um + sbend_len_um
    coup = np.array([(x_c0, y_c), (x_c0 + coupling_len_um, y_c)])
    right = left[::-1].copy()
    right[:, 0] = total_len - right[:, 0]
    full = gf.Path(_dedupe(np.vstack([left, coup, right])))
    coupler_only = gf.Path(coup)
    guide_len = float(full.length())
    coup_len = float(coupler_only.length())
    return {
        "arms": {
            "guide_full": guide_len,
            "guide_minus_coupler": guide_len - coup_len,
        },
        "delta_length_um": coup_len,
    }


if __name__ == "__main__":
    here = Path(__file__).parent
    component = directional_coupler()
    component.write_gds(here / "directional_coupler.gds", with_metadata=False)
    (here / "lengths.json").write_text(json.dumps(_measure_lengths(), indent=2))
