"""
Adiabatic 1x2 mode-evolution power splitter retargeted to 400 nm TFLN strip.

Same device as the Phase-A recreation (central input taper hands power to two
outer guides that grow from tips, then fan out to two 50/50 outputs), with the
platform constants adapted to this stack and the transfer length set from the
local supermode coupling length. Primitives only; layer (1, 0); gdsfactory 9.20.7.
"""

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np

LAYER = (1, 0)

# ---- PLATFORM CONSTANTS (rule-based from the stack, not searched) -------------
wg_width = 1.2          # um, single_mode_width_um for this stack
min_feature = 0.5       # um, min_feature_um for this stack

# ---- FUNCTION KNOBS (top-level tunables) --------------------------------------
input_straight_length = 2.0   # um, single-mode input access (center guide)
center_input_width = 1.2                  # um, center guide width at input (= wg)
center_tip_width = 0.5                     # um, center guide tip (= min_feature)
arm_tip_width = 0.5                        # um, outer guide starting tip (= min_feature)
arm_width = 1.2                            # um, output guide width (= wg)
coupling_gap = 0.30                        # um, center-outer edge gap (round-2 BEST: T=0.930)
arm_offset = 1.15                   # um, outer centerline = (wg+mf)/2 + coupling_gap = 0.85 + 0.30
taper_length = 115.0                      # um, ADIABATIC TRANSFER LENGTH (the key knob)
couple_straight_length = 1.0           # um, co-propagation straight after transfer
sbend_length = 28.0                      # um, fan-out S-bend length (sized to min_bend_radius)
output_offset = 3.0             # um, output half-separation (2x = center-to-center)
output_straight_length = 3.0             # um, output straight stub
delta_length = 0.0                          # um, top-arm path-length bias (balanced splitter at 0)

OUTPUT_GDS = "device_tfln400.gds"

# Geometry milestones along x (deterministic from the knobs).
X_TAPER0 = input_straight_length
X_TAPER_END = X_TAPER0 + taper_length
X_COUPLE_END = X_TAPER_END + couple_straight_length
X_SBEND_END = X_COUPLE_END + sbend_length
X_OUT_END = X_SBEND_END + output_straight_length


def _sbend_points(x0, y0, dx, dy, n=200):
    """Curvature-continuous sine S-bend from (x0, y0) to (x0+dx, y0+dy).

    y(t) = dy*(t - sin(2*pi*t)/(2*pi)): zero slope AND zero curvature at both
    ends (unlike a raised cosine, whose curvature jumps at entry), so the mode
    sees no abrupt bend at the junction. R_min = L^2 / (2*pi*dy).
    """
    t = np.linspace(0.0, 1.0, n)
    x = x0 + dx * t
    y = y0 + dy * (t - np.sin(2.0 * np.pi * t) / (2.0 * np.pi))
    return np.column_stack([x, y])


def _arclength(pts):
    return float(np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1)).sum())


def _arm_specs():
    # Balanced splitter; delta_length biases only the top arm's stub.
    return [("top", +1.0, delta_length), ("bottom", -1.0, 0.0)]


def _build(c):
    """Add all geometry to c; return the two output-arm path lengths (um)."""
    # --- Center guide: single-mode input straight, then wg -> tip taper ---
    center_in = gf.path.extrude(
        gf.path.straight(length=input_straight_length), width=center_input_width, layer=LAYER
    )
    c.add_ref(center_in)  # left edge at x=0, on axis
    center_taper = gf.components.taper(
        length=taper_length, width1=center_input_width, width2=center_tip_width, layer=LAYER
    )
    c.add_ref(center_taper).move((X_TAPER0, 0.0))

    arm_lengths = {}
    for name, sgn, extra in _arm_specs():
        y_couple = sgn * arm_offset
        y_out = sgn * output_offset

        # Outer guide: tip -> full width taper (the transfer region)
        arm_taper = gf.components.taper(
            length=taper_length, width1=arm_tip_width, width2=arm_width, layer=LAYER
        )
        c.add_ref(arm_taper).move((X_TAPER0, y_couple))

        # Co-propagation straight to finish the swap
        couple = gf.path.extrude(
            gf.path.straight(length=couple_straight_length), width=arm_width, layer=LAYER
        )
        c.add_ref(couple).move((X_TAPER_END, y_couple))

        # Gentle fan-out S-bend, then output stub
        sb = _sbend_points(X_COUPLE_END, y_couple, sbend_length, y_out - y_couple)
        c.add_ref(gf.path.extrude(gf.Path(sb), width=arm_width, layer=LAYER))
        straight = gf.path.extrude(
            gf.path.straight(length=output_straight_length + extra), width=arm_width, layer=LAYER
        )
        c.add_ref(straight).move((X_SBEND_END, y_out))

        arm_lengths[name] = (
            taper_length + couple_straight_length + _arclength(sb)
            + output_straight_length + extra
        )
    return arm_lengths


@gf.cell
def splitter():
    c = gf.Component()
    _build(c)
    return c


def _write_lengths(arm_lengths):
    top, bottom = arm_lengths["top"], arm_lengths["bottom"]
    Path("lengths.json").write_text(json.dumps(
        {"arms": {"top": top, "bottom": bottom}, "delta_length_um": abs(top - bottom)}, indent=2
    ))


if __name__ == "__main__":
    comp = splitter()
    flat = comp.copy()
    flat.flatten()  # expose geometry at top level (kfactory $$$CONTEXT gotcha)
    flat.write_gds(OUTPUT_GDS)
    _write_lengths(_build(gf.Component()))
