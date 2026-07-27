"""
Symmetric 2x2 directional coupler with tapered access — primitives-only,
parametric recreation.

Topology: each of two waveguides enters at a narrow port tip, linearly tapers
up to the device width along a straight access section, S-bends inward to a
central region where the two guides run parallel at a small constant gap for
`coupling_length` (the transfer length), then S-bends back out and tapers back
down to a narrow output tip. Classic evanescent directional coupler with
adiabatic access tapers (not an MMI, not a Y-branch).

Built from primitives only: gf.Path centerlines extruded with constant / linear-
transition cross-sections on layer (1,0). Two guides = two arms (mirror in y).
Run `python device.py` -> writes device.gds and lengths.json next to it.
"""
import json
import os

import numpy as np
import gdsfactory as gf

# ----------------------------------------------------------------------------
# Top-level tunables (parametric contract; JEE / knob-response substitutable).
# All function-defining knobs of the tapered coupler are here.
# ----------------------------------------------------------------------------
tip_width = 0.284         # um  waveguide width at the port tips (access / edge coupling)
device_width = 0.354      # um  waveguide width through the bends and coupling region
coupling_gap = 0.106     # um  edge-to-edge gap in the coupling region (sets kappa)
coupling_length = 56.0   # um  parallel interaction / transfer length (sets split ratio)
sbend_length = 13.0      # um  horizontal length of each S-bend (access routing)
taper_length = 19.0      # um  length of each access taper (tip_width -> device_width)
input_port_sep = 3.46    # um  center-to-center separation of the input (left) ports
output_port_sep = 3.67   # um  center-to-center separation of the output (right) ports
sbend_steepness = 1.5    # S-bend shape: 0 -> raised cosine; >0 -> steeper middle
# total device length = 2*taper_length + 2*sbend_length + coupling_length

LAYER = (1, 0)
_N_BEND = 200            # samples per S-bend

_KNOBS = ("tip_width", "device_width", "coupling_gap", "coupling_length",
          "sbend_length", "taper_length", "input_port_sep", "output_port_sep",
          "sbend_steepness")


def _snap(w):
    """gdsfactory needs cross-section widths on a 0.002 um (2 dbu) grid."""
    return round(w / 0.002) * 0.002


def _frac(t, steep):
    """Normalized S-offset in [0,1] with zero-ish slope at both ends."""
    if steep <= 0:
        return (1.0 - np.cos(np.pi * t)) / 2.0
    return (np.tanh(steep * (2.0 * t - 1.0)) / np.tanh(steep) + 1.0) / 2.0


def _bend_pts(x0, y0, dx, dy, steep):
    t = np.linspace(0.0, 1.0, _N_BEND)
    return np.column_stack([x0 + dx * t, y0 + dy * _frac(t, steep)])


def _guide_segments(sign, P):
    """Three centerline Paths for one guide (sign=+1 top, -1 bottom):
    (input taper straight, middle bend+coupling+bend, output taper straight).
    Device centered on y=0, x running 0 .. total_length.
    """
    coupling_sep = P["coupling_gap"] + P["device_width"]   # center-to-center in coupling
    y_in = sign * P["input_port_sep"] / 2.0
    y_out = sign * P["output_port_sep"] / 2.0
    y_coup = sign * coupling_sep / 2.0
    Lt, Ls, Lc = P["taper_length"], P["sbend_length"], P["coupling_length"]
    steep = P["sbend_steepness"]

    x_b1 = Lt                       # start of input bend
    x_c0 = Lt + Ls                  # start of coupling
    x_c1 = Lt + Ls + Lc             # end of coupling
    x_b2e = Lt + 2 * Ls + Lc        # end of output bend
    x_end = x_b2e + Lt

    path_in = gf.Path([(0.0, y_in), (x_b1, y_in)])

    mid = [(x_b1, y_in)]
    mid += _bend_pts(x_b1, y_in, Ls, y_coup - y_in, steep)[1:].tolist()
    mid += [(x_c1, y_coup)]
    mid += _bend_pts(x_c1, y_coup, Ls, y_out - y_coup, steep)[1:].tolist()
    path_mid = gf.Path(mid)

    path_out = gf.Path([(x_b2e, y_out), (x_end, y_out)])
    return path_in, path_mid, path_out


def _params(**over):
    P = {k: globals()[k] for k in _KNOBS}
    P.update(over)
    return P


def build(**over):
    """Build the tapered coupler Component from the current tunables (+ overrides)."""
    P = _params(**over)
    tip_cs = gf.cross_section.cross_section(width=_snap(P["tip_width"]), layer=LAYER)
    dev_cs = gf.cross_section.cross_section(width=_snap(P["device_width"]), layer=LAYER)
    taper_in = gf.path.transition(tip_cs, dev_cs, width_type="linear")   # tip -> device
    taper_out = gf.path.transition(dev_cs, tip_cs, width_type="linear")  # device -> tip

    c = gf.Component()
    for sign in (+1, -1):
        p_in, p_mid, p_out = _guide_segments(sign, P)
        c.add_ref(gf.path.extrude_transition(p_in, taper_in))
        c.add_ref(p_mid.extrude(dev_cs))
        c.add_ref(gf.path.extrude_transition(p_out, taper_out))
    return c, P


@gf.cell
def directional_coupler():
    return build()[0]


def _arm_length(sign, P):
    return float(sum(p.length() for p in _guide_segments(sign, P)))


def _write_lengths(directory, P):
    """Write lengths.json (measurement contract): two arms + their delta."""
    arms = {"top": _arm_length(+1, P), "bottom": _arm_length(-1, P)}
    delta = abs(arms["top"] - arms["bottom"])
    with open(os.path.join(directory, "lengths.json"), "w") as f:
        json.dump({"arms": arms, "delta_length_um": delta}, f, indent=2)
    return arms, delta


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    comp, P = build()
    comp.write_gds(os.path.join(here, "device.gds"))
    arms, delta = _write_lengths(here, P)
    print(f"wrote device.gds  arms={arms}  delta_length_um={delta:.4f}")
    print(f"bbox size um: {comp.xsize:.3f} x {comp.ysize:.3f}")
