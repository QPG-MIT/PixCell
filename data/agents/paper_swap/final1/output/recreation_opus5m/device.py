"""Adiabatic (mode-evolution) 1x2 3-dB power splitter -- primitives only.

Topology: a wide input bus tapers DOWN to a narrow tip while two symmetric
outer guides, starting as narrow tips across a small gap, taper UP to full
width.  The fundamental supermode starts localized on the bus and, if the
width variation is slow compared with the supermode beat length, adiabatically
evolves into the even combination of the two outer guides -> broadband,
fabrication-tolerant 50/50 split.  Sine S-bends then route the arms to the
output pitch.

Built from primitives only: gf.Path + extrude / extrude_transition
(straight, linear-width taper, sine S-bend centerline).  No component stencils,
no raw polygons.
"""

from __future__ import annotations

import json

import numpy as np
import gdsfactory as gf

# ---------------------------------------------------------------------------
# Tunables (top-level, JEE-substitutable).  All lengths in microns.
# ---------------------------------------------------------------------------

layer = (1, 0)

# --- platform widths -------------------------------------------------------
bus_width_um = 0.2700  # input bus width (widest guide -> mode starts here)
arm_width_um = 0.2420  # terminal width of each output arm

# --- FUNCTION knobs: adiabatic mode evolution ------------------------------
bus_tip_width_um = 0.0720  # bus width at hand-off; too wide -> radiation loss
arm_tip_width_um = 0.0660  # arm width at the start; sets the index start point
coupler_gap_um = 0.0999  # bus-edge to arm-edge gap -> supermode anticrossing
bus_taper_length_um = 21.8569  # transfer length of the bus down-taper
arm_taper_length_um = 22.4950  # transfer length of the arm up-taper

# --- FUNCTION knobs: output routing ---------------------------------------
sbend_length_um = 10.7178  # S-bend run (adiabaticity of the routing bend)
out_offset_um = 0.7295  # output arm half-pitch (each arm's final |y|)
out_straight_um = 3.7129  # output straights

# --- layout placement ------------------------------------------------------
bus_straight_um = 3.2178  # bus straight before the down-taper begins
arm_start_x_um = 3.0693  # x where the arm tips begin
sbend_npoints = 201
# Vertical offsets of the coupler region.  These are NOT device features: the
# source drawing places the bus ~5 px and the arm pair ~3.25 px above the
# midline while its outputs are exactly symmetric.  Reproduced for fidelity;
# set both to 0.0 for the physically symmetric device.
bus_y_offset_um = 0.0163
arm_y_offset_um = 0.0130

# Derived: arm centerline offset from the optical axis in the coupler region.
arm_offset_um = bus_width_um / 2 + coupler_gap_um + arm_tip_width_um / 2


# ---------------------------------------------------------------------------
# Primitive builders
# ---------------------------------------------------------------------------


def _snap(width: float) -> float:
    """Widths must be an even number of dbu (1 dbu = 1 nm) in gdsfactory 9.20.7."""
    return round(width / 0.002) * 0.002


def _xs(width: float):
    return gf.cross_section.cross_section(width=_snap(width), layer=layer)


def _linear_taper(length: float, w1: float, w2: float) -> gf.Component:
    """Straight path extruded through a linear width transition."""
    trans = gf.path.transition(_xs(w1), _xs(w2), width_type="linear")
    return gf.path.straight(length=length, npoints=2).extrude_transition(trans)


def _sine_sbend_path(length: float, dy: float) -> gf.Path:
    """Sine S-bend centerline: y(t) = dy * (t - sin(2 pi t) / (2 pi)); flat ends."""
    t = np.linspace(0.0, 1.0, sbend_npoints)
    x = t * length
    y = dy * (t - np.sin(2 * np.pi * t) / (2 * np.pi))
    return gf.Path(np.column_stack([x, y]))


def _sine_sbend(length: float, dy: float, width: float) -> gf.Component:
    return _sine_sbend_path(length, dy).extrude(_xs(width))


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


@gf.cell
def adiabatic_splitter() -> gf.Component:
    c = gf.Component()

    # --- input bus: straight, then down-taper to the hand-off tip ----------
    bus_in = c << gf.path.straight(length=bus_straight_um).extrude(_xs(bus_width_um))
    bus_in.dmove((0.0, bus_y_offset_um))

    bus_taper = c << _linear_taper(bus_taper_length_um, bus_width_um, bus_tip_width_um)
    bus_taper.dmove((bus_straight_um, bus_y_offset_um))

    # --- two arms, mirrored about the optical axis -------------------------
    for sign in (+1, -1):
        y_coupler = sign * arm_offset_um + arm_y_offset_um
        y_out = sign * out_offset_um
        dy = y_out - y_coupler

        arm_taper = c << _linear_taper(arm_taper_length_um, arm_tip_width_um, arm_width_um)
        arm_taper.dmove((arm_start_x_um, y_coupler))

        sbend = c << _sine_sbend(sbend_length_um, dy, arm_width_um)
        sbend.dmove((arm_start_x_um + arm_taper_length_um, y_coupler))

        out = c << gf.path.straight(length=out_straight_um).extrude(_xs(arm_width_um))
        out.dmove((arm_start_x_um + arm_taper_length_um + sbend_length_um, y_out))

    return c


def write_lengths(path: str = "lengths.json") -> dict:
    """Measured centerline path lengths, computed from the gf.Path objects.

    Never hand-entered.  `delta_length_um` is the upper/lower arm path-length
    imbalance (magnitude) -- identically zero for the physically symmetric
    device, which is the property that keeps the split 50/50 and phase-matched.
    """
    arms = {}
    for name, sign in (("upper", +1), ("lower", -1)):
        y_coupler = sign * arm_offset_um + arm_y_offset_um
        dy = sign * out_offset_um - y_coupler
        arms[name] = float(
            arm_taper_length_um
            + _sine_sbend_path(sbend_length_um, dy).length()
            + out_straight_um
        )
    data = {
        "arms": arms,
        "bus_length_um": float(bus_straight_um + bus_taper_length_um),
        "delta_length_um": abs(float(arms["upper"] - arms["lower"])),
    }
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)
    return data


if __name__ == "__main__":
    comp = adiabatic_splitter()
    bb = comp.dbbox()
    print(f"bbox um: x {bb.left:.4f}..{bb.right:.4f}  y {bb.bottom:.4f}..{bb.top:.4f}")
    print(f"size um: {bb.right - bb.left:.4f} x {bb.top - bb.bottom:.4f}")
    # with_metadata=False: kfactory's $$$CONTEXT_INFO$$$ cell references the
    # top cell, which would leave the GDS with no real top-level cell and make
    # area-based checks read zero.
    comp.write_gds("device.gds", with_metadata=False)
    print("wrote device.gds")
    print(write_lengths())
