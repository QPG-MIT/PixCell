"""Symmetric 2x2 evanescent directional coupler.

Two identical strip waveguides run straight at the four ports, are pulled
together by mirror-symmetric cosine S-bends, run parallel over a short
coupling straight (where the evanescent tails overlap and power beats between
the symmetric and antisymmetric supermodes), then separate through the
mirrored S-bends.

Primitives only: each centerline is built as a gf.Path point array and given
material by gf.path.extrude with a constant-width cross section. No
gf.components device stencils, no raw polygons.

gdsfactory 9.20.7 / layer (1, 0).
"""

import json
from pathlib import Path as _Path

import numpy as np
import gdsfactory as gf

# ---------------------------------------------------------------- tunables
# Function-defining knobs of the coupler (all in micrometres).
wg_width_um = 0.656  # strip width -> mode confinement, single-mode condition
coupling_gap_um = 0.317  # edge-to-edge gap in the parallel section -> kappa
coupling_length_um = 2.455  # parallel straight length -> accumulated kappa*L
bend_length_um = 6.955  # S-bend longitudinal extent -> adiabaticity
input_separation_um = 2.342  # port center-to-center separation at the facets
straight_in_um = 0.8175  # straight lead-in at each facet

# Discretisation / process constants.
bend_npoints = 401
layer = (1, 0)


def _arm_centerline(
    sign: float,
    straight_in: float,
    bend_length: float,
    coupling_length: float,
    y_outer: float,
    y_inner: float,
    npoints: int,
) -> np.ndarray:
    """Centerline of one coupler arm: straight - S - straight - S - straight.

    ``sign`` = +1 for the upper arm, -1 for the lower arm.
    """
    x1 = straight_in
    x2 = x1 + bend_length
    x3 = x2 + coupling_length
    x4 = x3 + bend_length
    total = x4 + straight_in

    t = np.linspace(0.0, 1.0, npoints)
    ramp = 0.5 * (1.0 - np.cos(np.pi * t))  # 0 -> 1, zero slope at both ends

    x = np.concatenate([[0.0], x1 + bend_length * t, x3 + bend_length * t, [total]])
    y = np.concatenate(
        [
            [y_outer],
            y_outer + (y_inner - y_outer) * ramp,
            y_inner + (y_outer - y_inner) * ramp,
            [y_outer],
        ]
    )
    y = sign * y

    # drop duplicate x (segment junctions) so the Path has no zero-length steps
    keep = np.concatenate([[True], np.diff(x) > 1e-9])
    return np.column_stack([x[keep], y[keep]])


def _polyline_length(pts: np.ndarray) -> float:
    return float(np.sum(np.hypot(np.diff(pts[:, 0]), np.diff(pts[:, 1]))))


@gf.cell
def directional_coupler(
    wg_width: float = wg_width_um,
    coupling_gap: float = coupling_gap_um,
    coupling_length: float = coupling_length_um,
    bend_length: float = bend_length_um,
    input_separation: float = input_separation_um,
    straight_in: float = straight_in_um,
    npoints: int = bend_npoints,
) -> gf.Component:
    c = gf.Component()

    y_outer = 0.5 * input_separation
    y_inner = 0.5 * (coupling_gap + wg_width)

    for sign in (+1.0, -1.0):
        pts = _arm_centerline(
            sign, straight_in, bend_length, coupling_length, y_outer, y_inner, npoints
        )
        path = gf.Path(pts)
        c << gf.path.extrude(path, layer=layer, width=wg_width)

    return c


def measure(**kwargs) -> dict:
    """Lengths measured from this script's OWN centerline geometry.

    The two reported "arms" are one guide's total optical path through the
    device and the same guide's path OUTSIDE the parallel interaction section.
    Their difference is the coupler's interaction length — the length that sets
    the accumulated coupling phase kappa*L, and the coupler's analogue of an
    MZI's arm-length imbalance. (The two physical guides are identical by
    symmetry, so a top-vs-bottom difference would be identically zero and would
    measure nothing.)
    """
    p = dict(
        straight_in=kwargs.get("straight_in", straight_in_um),
        bend_length=kwargs.get("bend_length", bend_length_um),
        coupling_length=kwargs.get("coupling_length", coupling_length_um),
        y_outer=0.5 * kwargs.get("input_separation", input_separation_um),
        y_inner=0.5 * (kwargs.get("coupling_gap", coupling_gap_um) + kwargs.get("wg_width", wg_width_um)),
        npoints=kwargs.get("npoints", bend_npoints),
    )
    pts = _arm_centerline(+1.0, **p)
    total_path = _polyline_length(pts)

    x2 = p["straight_in"] + p["bend_length"]
    x3 = x2 + p["coupling_length"]
    mask = (pts[:, 0] >= x2 - 1e-9) & (pts[:, 0] <= x3 + 1e-9)
    coupled_path = _polyline_length(pts[mask])

    return {
        "arms": {
            "guide_total_path": total_path,
            "guide_path_outside_coupler": total_path - coupled_path,
        },
        "delta_length_um": coupled_path,
        "device_length_um": float(pts[-1, 0]),
    }


if __name__ == "__main__":
    here = _Path(__file__).resolve().parent
    component = directional_coupler()
    # with_metadata=False keeps the $$$CONTEXT_INFO$$$ cell out of the file, so the
    # coupler cell is the true top level and downstream area/bbox readers see it.
    component.write_gds(str(here / "device.gds"), with_metadata=False)
    (here / "lengths.json").write_text(json.dumps(measure(), indent=2))
    print(component.dbbox())
