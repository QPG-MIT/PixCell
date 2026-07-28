"""Subwavelength-grating (multi-box) metamaterial directional coupler.

Primitives only: gf.Path centrelines (straight + circular-arc segments)
extruded at constant width onto layer (1, 0).  No gf.components stencils,
no raw polygons.

Lattice picture (this is the whole device):
    one uniform lateral lattice of period `pitch_um` along y.
      |k| <= n_gap_strips//2          -> isolated SWG strips (shared gap array)
      next `n_bus_sites` sites        -> filled solid = the guiding rail (bus)
      next `n_clad_strips` sites      -> isolated SWG strips (outer multi-box cladding)
    mirrored about y = 0.
The gap array runs straight through the frame; each arm (rail + cladding)
fans away at both ends on its own circular arc.
"""

import json

import numpy as np
import gdsfactory as gf

# ---------------------------------------------------------------- tunables
# metamaterial lattice
pitch_um = 0.1004  # lateral SWG period (must stay << lambda / 2 n_eff)
strip_width_um = 0.068  # strip width -> duty cycle = strip_width_um / pitch_um

# transverse composition of one half of the cross-section
gap_strip_width_um = 0.068  # duty cycle of the shared gap array (can differ
# from the cladding duty cycle: it sets the metamaterial index of the bridge)

n_gap_strips = 5  # SWG strips bridging the two arms (coupling knob)
n_bus_sites = 5  # lattice sites filled solid to form the rail
n_clad_strips = 5  # outer multi-box cladding strips per arm

# longitudinal layout
total_length_um = 120.0  # framed window length
coupling_length_um = 99.7  # straight interaction length

# fan-out law: curvature grows linearly with lattice index
bend_curvature_per_period = 0.02570  # d(1/R) per lattice index
bend_curvature_zero_index = 1.305  # lattice index of zero curvature
fan_exit_y_um = 2.30  # arcs are drawn until they clear the window
fan_exit_bias_um = 0.0029  # top arm drawn slightly further out: the figure is not
# perfectly mirror symmetric (top features sit ~1.5 nm lower than the mirror of the
# bottom ones); biasing the top exit registers the whole pattern to the frame.
gap_array_offset_um = -0.0052  # measured offset of the shared SWG gap array
# relative to the two arms (present in the source figure)

# multi-box -> solid strip transition.  Where an arm leaves the coupling region
# its cladding strips widen (duty cycle -> 1) so the metamaterial cladding
# merges adiabatically into the solid access waveguide that routes away.
clad_merge_rate_per_um = 0.045  # d(width)/d(arc length) in the fan-out
clad_merge_max_width_um = 0.22  # widening stops here
bus_merge_rate_per_um = 0.0  # the rail keeps its width through the fan-out
taper_steps = 48  # discretisation of the width taper along each arc

layer = (1, 0)


# ---------------------------------------------------------------- helpers
def _lattice_y(k: float) -> float:
    """Centre of lattice site k, in um."""
    return k * pitch_um


def _straight_points(y: float, x0: float, x1: float, n: int = 2) -> np.ndarray:
    x = np.linspace(x0, x1, n)
    return np.column_stack([x, np.full_like(x, y)])


def _fan_points(y: float, radius: float, x_left: float, x_right: float,
                y_exit: float, n_arc: int = 160) -> np.ndarray:
    """Straight run between the two bend starts, with an upward circular arc
    at each end drawn until the centreline reaches ``y_exit``."""
    dy = y_exit - y
    cos_end = 1.0 - dy / radius
    theta = np.arccos(np.clip(cos_end, -1.0, 1.0))

    t = np.linspace(0.0, theta, n_arc)
    arc_dx = radius * np.sin(t)
    arc_dy = radius * (1.0 - np.cos(t))

    arc_s = radius * t  # arc length from the bend start
    left = np.column_stack([x_left - arc_dx[::-1], y + arc_dy[::-1]])
    mid = _straight_points(y, x_left, x_right)
    right = np.column_stack([x_right + arc_dx, y + arc_dy])
    return left, mid, right, arc_s


def _radius(k: float) -> float:
    curvature = bend_curvature_per_period * (k - bend_curvature_zero_index)
    return 1.0 / curvature


def _snap(width: float) -> float:
    """kfactory requires extrusion widths on a 2 dbu (0.002 um) grid."""
    return round(width / 0.002) * 0.002


def _extrude(points: np.ndarray, width: float) -> gf.Component:
    return gf.Path(points).extrude(width=_snap(width), layer=layer)


def _add_element(c: gf.Component, y: float, radius: float, x_left: float,
                 x_right: float, exit_y: float, width: float, rate: float,
                 max_width: float, mirror: bool) -> None:
    """One lattice element: straight run + a fan-out arc at each end whose
    width tapers with arc length (the multi-box -> strip transition)."""
    left, mid, right, arc_s = _fan_points(y, radius, x_left, x_right, exit_y)
    flip = np.array([1.0, -1.0]) if mirror else np.array([1.0, 1.0])

    c.add_ref(_extrude(mid * flip, width))

    n = len(arc_s)
    edges = np.linspace(0, n - 1, taper_steps + 1).astype(int)
    for a, b in zip(edges[:-1], edges[1:]):
        w = min(max_width, width + rate * 0.5 * (arc_s[a] + arc_s[b]))
        c.add_ref(_extrude(right[a:b + 1] * flip, w))
        lo, hi = n - 1 - b, n - 1 - a
        c.add_ref(_extrude(left[lo:hi + 1] * flip, w))


# ---------------------------------------------------------------- assembly
@gf.cell
def swg_metamaterial_coupler() -> gf.Component:
    c = gf.Component()

    x_left = 0.5 * (total_length_um - coupling_length_um)
    x_right = total_length_um - x_left

    # --- shared SWG gap array: straight across the whole window ---------
    k_gap_max = (n_gap_strips - 1) / 2.0
    for i in range(n_gap_strips):
        k = -k_gap_max + i
        pts = _straight_points(_lattice_y(k) + gap_array_offset_um, 0.0,
                               total_length_um)
        c.add_ref(_extrude(pts, gap_strip_width_um))

    # --- the two arms: solid rail + outer multi-box cladding ------------
    k_bus_first = k_gap_max + 1.0  # first filled lattice site
    k_bus_centre = k_bus_first + (n_bus_sites - 1) / 2.0
    bus_width_um = (n_bus_sites - 1) * pitch_um + strip_width_um

    for sign in (+1.0, -1.0):
        # rail
        exit_y = fan_exit_y_um + (fan_exit_bias_um if sign > 0 else 0.0)
        mirror = sign < 0
        _add_element(c, _lattice_y(k_bus_centre), _radius(k_bus_centre),
                     x_left, x_right, exit_y, bus_width_um,
                     bus_merge_rate_per_um, bus_width_um + 1.0, mirror)

        # outer cladding strips
        for j in range(n_clad_strips):
            k = k_bus_first + n_bus_sites + j
            _add_element(c, _lattice_y(k), _radius(k), x_left, x_right,
                         exit_y, strip_width_um, clad_merge_rate_per_um,
                         clad_merge_max_width_um, mirror)

    return c


def _path_length(points: np.ndarray) -> float:
    return float(np.sum(np.hypot(*np.diff(points, axis=0).T)))


def write_lengths(path: str = "lengths.json") -> dict:
    """Centreline lengths measured from the same gf.Path point arrays that are
    extruded into the GDS -- never hand-entered.

    This is a coupler, not an MZI: the two arms are mirror images, so the
    arm imbalance ``delta_length_um`` is zero by construction.  The device's
    length knob is ``coupling_length_um`` (also reported), the straight
    interaction length over which the two arms exchange power.
    """
    x_left = 0.5 * (total_length_um - coupling_length_um)
    x_right = total_length_um - x_left
    k_gap_max = (n_gap_strips - 1) / 2.0
    k_bus_centre = k_gap_max + 1.0 + (n_bus_sites - 1) / 2.0

    left, mid, right, _ = _fan_points(_lattice_y(k_bus_centre),
                                      _radius(k_bus_centre), x_left, x_right,
                                      fan_exit_y_um)
    straight = _path_length(mid)
    arm = _path_length(np.vstack([left, mid, right]))

    data = {
        "arms": {
            "arm_top_rail_um": arm,
            "arm_bottom_rail_um": arm,
        },
        "gap_array_strip_um": total_length_um,
        "coupling_length_um": straight,
        "delta_length_um": 0.0,
    }
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)
    return data


if __name__ == "__main__":
    component = swg_metamaterial_coupler().copy()
    # merge the per-segment extrusions into one flat cell so that downstream
    # readers (gdstk top_level) see the polygons directly
    component.flatten()
    component.write_gds("device.gds")
    print("bbox:", component.bbox())
    print("lengths:", write_lengths())
