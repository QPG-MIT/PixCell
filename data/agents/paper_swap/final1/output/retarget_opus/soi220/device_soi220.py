"""
Adiabatic 1x2 mode-evolution power splitter retargeted to 220 nm SOI strip.

BEST soi220 device (round 1): measured T=0.928, balance 0.500. On strong-confinement
SOI the tighter merged-regime gap (mf/2) outperformed the unmerged gap=mf variant
that cleared SiN -- opening the gap regressed SOI on both transmission and balance,
so the round-1 geometry is the honest best within the cap. Primitives only; layer
(1, 0); gdsfactory 9.20.7.
"""

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np

LAYER = (1, 0)

# ---- PLATFORM CONSTANTS (rule-based from the stack, not searched) -------------
wg_width = 0.5           # um, single_mode_width_um for this stack
min_feature = 0.18       # um, min_feature_um for this stack

# ---- FUNCTION KNOBS (top-level tunables) --------------------------------------
input_straight_length = 2.0   # um, single-mode input access (center guide)
center_input_width = 0.5      # um, center guide width at input (= wg)
center_tip_width = 0.18       # um, center guide tip (= min_feature)
arm_tip_width = 0.18          # um, outer guide starting tip (= min_feature)
arm_width = 0.5               # um, output guide width (= wg)
coupling_gap = 0.18           # um, nominal coupling gap (= min_feature)
arm_offset = 0.43             # um, outer centerline in coupling region (= wg/2 + coupling_gap)
taper_length = 38.0           # um, ADIABATIC TRANSFER LENGTH (the key knob)
couple_straight_length = 2.0  # um, co-propagation straight after transfer
sbend_length = 12.0           # um, fan-out S-bend length
output_offset = 3.0           # um, output half-separation (2x = center-to-center)
output_straight_length = 3.0  # um, output straight stub
delta_length = 0.0            # um, top-arm path-length bias (balanced splitter at 0)

OUTPUT_GDS = "device_soi220.gds"

# Geometry milestones along x (deterministic from the knobs).
X_TAPER0 = input_straight_length
X_TAPER_END = X_TAPER0 + taper_length
X_COUPLE_END = X_TAPER_END + couple_straight_length
X_SBEND_END = X_COUPLE_END + sbend_length
X_OUT_END = X_SBEND_END + output_straight_length


def _sbend_points(x0, y0, dx, dy, n=200):
    """Raised-cosine S-bend centerline from (x0, y0) to (x0+dx, y0+dy)."""
    t = np.linspace(0.0, 1.0, n)
    x = x0 + dx * t
    y = y0 + dy * (0.5 - 0.5 * np.cos(np.pi * t))
    return np.column_stack([x, y])


def _arclength(pts):
    return float(np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1)).sum())


def _arm_specs():
    return [("top", +1.0, delta_length), ("bottom", -1.0, 0.0)]


def _build(c):
    """Add all geometry to c; return the two output-arm path lengths (um)."""
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

        arm_taper = gf.components.taper(
            length=taper_length, width1=arm_tip_width, width2=arm_width, layer=LAYER
        )
        c.add_ref(arm_taper).move((X_TAPER0, y_couple))

        couple = gf.path.extrude(
            gf.path.straight(length=couple_straight_length), width=arm_width, layer=LAYER
        )
        c.add_ref(couple).move((X_TAPER_END, y_couple))

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
    flat.flatten()
    flat.write_gds(OUTPUT_GDS)
    _write_lengths(_build(gf.Component()))
