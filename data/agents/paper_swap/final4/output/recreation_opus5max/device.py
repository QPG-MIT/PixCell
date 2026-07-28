"""Symmetric 2x2 evanescent directional coupler — primitives-only parametric build.

Topology (recovered from data/agents/paper_swap/final4/device_bw.png):

    port_straight   S-bend in     coupling_length    S-bend out   port_straight
    ==========\\__                ______________                __/==========
                 \\______________/  gap          \\______________/
                  ______________                 ______________
    ==========/‾‾               \\‾‾‾‾‾‾‾‾‾‾‾‾‾‾/               ‾‾\\==========

Two identical single-mode guides run in at a large separation, S-bend toward the
optical axis, run parallel across a sub-wavelength gap where their evanescent
tails overlap, then S-bend symmetrically apart.  Light beats between the guides
over the coupling length Lpi = lambda / (2 (n_sym - n_antisym)); the splitting
ratio is set by `coupler_gap` (exponential) and `coupling_length` (linear),
with `wg_width` setting n_eff / the evanescent decay length.

Everything is built from primitives: gf.path.straight, a cubic-Bezier S-bend
expressed as a gf.Path, and Path.extrude.  No gf.components device stencils,
no raw polygons.
"""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np

# --------------------------------------------------------------------------
# Tunables (top-level `name = value`, JEE-substitutable).
# The FUNCTION knobs of a directional coupler are coupler_gap, coupling_length,
# wg_width, sbend_offset and sbend_length; port_straight is routing only.
# --------------------------------------------------------------------------
wg_width = 0.658
coupler_gap = 0.293
coupling_length = 0.028
sbend_length = 8.216
sbend_offset = 0.6934
port_straight = 0.770
sbend_c1 = 0.40
sbend_c2 = 0.39
sbend_npoints = 601
layer_number = 1
layer_datatype = 0


def layer_spec() -> tuple[int, int]:
    return (int(layer_number), int(layer_datatype))


# --------------------------------------------------------------------------
# Primitive path pieces
# --------------------------------------------------------------------------
def sbend_path(dx: float, dy: float, npoints: int = 601, mirror: bool = False) -> gf.Path:
    """Cubic-Bezier S-bend centerline as a gf.Path.

    Control polygon (0,0) (c1*dx, 0) (c2*dx, dy) (dx, dy):
        x(u) = dx [3(1-u)^2 u c1 + 3(1-u) u^2 c2 + u^3]
        y(u) = dy u^2 (3 - 2u)
    c1 = c2 = 0.5 is the textbook symmetric S-bend; the fractions are left free
    because the target's bend leaves the port early and approaches the coupling
    region asymptotically (fitted c1 = 0.40, c2 = 0.39).

    `mirror` reflects the curve through its own midpoint in x, which is what the
    OUTPUT bend of a device symmetric about its midline must be: the control
    fractions become (1 - c2, 1 - c1).  Both ends leave/enter horizontally, so
    segments join by pure translation.
    """
    c1, c2 = (1.0 - sbend_c2, 1.0 - sbend_c1) if mirror else (sbend_c1, sbend_c2)
    u = np.linspace(0.0, 1.0, int(npoints))
    x = dx * (3.0 * (1.0 - u) ** 2 * u * c1 + 3.0 * (1.0 - u) * u**2 * c2 + u**3)
    y = dy * (u**2 * (3.0 - 2.0 * u))
    return gf.Path(np.column_stack([x, y]))


def join(segments: list[gf.Path]) -> gf.Path:
    """Join horizontal-ended path primitives end-to-end by exact translation.

    gf.Path.append re-aligns on the *discretised* start angle, which rotates a
    sampled Bezier by ~1e-3 rad and drags its endpoint off by ~1% of dy.  Every
    segment here starts and ends horizontal by construction, so translation is
    the exact join.
    """
    points = np.asarray(segments[0].points, dtype=float)
    for segment in segments[1:]:
        nxt = np.asarray(segment.points, dtype=float)
        points = np.vstack([points, nxt[1:] + (points[-1] - nxt[0])])
    return gf.Path(points)


def arm_path(direction: float) -> gf.Path:
    """One coupler arm; direction=+1 is the upper guide (bends down), -1 lower."""
    sep_coupling = coupler_gap + wg_width
    y_port = direction * (sep_coupling / 2.0 + sbend_offset)
    path = join(
        [
            gf.path.straight(length=port_straight),
            sbend_path(sbend_length, -direction * sbend_offset, sbend_npoints),
            gf.path.straight(length=coupling_length),
            sbend_path(sbend_length, direction * sbend_offset, sbend_npoints, mirror=True),
            gf.path.straight(length=port_straight),
        ]
    )
    path.movey(y_port)
    return path


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------
@gf.cell
def directional_coupler() -> gf.Component:
    """Symmetric 2x2 directional coupler on layer (1, 0)."""
    component = gf.Component()
    for direction in (1.0, -1.0):
        component.add_ref(
            arm_path(direction).extrude(layer=layer_spec(), width=wg_width)
        )
    return component


def build(outdir: Path | None = None) -> dict:
    outdir = Path(__file__).resolve().parent if outdir is None else Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    component = directional_coupler()
    gds_path = outdir / "device.gds"
    # with_metadata=False: kfactory's $$$CONTEXT_INFO$$$ cell *references* every
    # other cell, so with metadata on it becomes the only GDS top-level cell —
    # and any reader that (rightly) skips $$$ cells then measures zero area.
    component.write_gds(gds_path, with_metadata=False)

    upper = arm_path(1.0)
    lower = arm_path(-1.0)
    upper_um = float(upper.length())
    lower_um = float(lower.length())

    # Measured from the gf.Path objects above — never hand-entered.
    lengths = {
        "device": "directional_coupler",
        "arms": {"upper_um": upper_um, "lower_um": lower_um},
        "delta_length_um": abs(upper_um - lower_um),
        "delta_length_note": (
            "0 by construction, not by omission: a symmetric directional coupler is "
            "phase matched, so its two arms are congruent and no knob can make them "
            "differ. The function-defining lengths of this device are the parallel "
            "coupling_length and the gap, reported below."
        ),
        "coupling_length_um": float(coupling_length),
        "coupler_gap_um": float(coupler_gap),
        "centerline_separation_coupling_um": float(coupler_gap + wg_width),
        "centerline_separation_ports_um": float(
            coupler_gap + wg_width + 2.0 * sbend_offset
        ),
        "wg_width_um": float(wg_width),
        "total_length_um": float(2.0 * port_straight + 2.0 * sbend_length + coupling_length),
        "bbox_um": [
            float(component.dbbox().left),
            float(component.dbbox().bottom),
            float(component.dbbox().right),
            float(component.dbbox().top),
        ],
    }
    (outdir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    return lengths


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
else:
    build()
