"""
Adiabatic 1x2 mode-evolution power splitter (three-waveguide adiabatic coupler).

Recreation of experiments/paper_swap/final1/device_bw.png, primitives-only.

Topology: a central input taper (wide -> point) hands its fundamental-mode power
adiabatically to two outer waveguides that grow from fine tips to full width; the
two outer guides then S-bend apart into two separated 50/50 outputs.

Primitives only: gf.components.taper, gf.path.straight/extrude, gf.Path from
points (raised-cosine S-bend). Geometry on layer (1, 0). gdsfactory 9.20.7.
"""

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np

LAYER = (1, 0)

# ---- FUNCTION KNOBS (top-level tunables) --------------------------------------
# Central input taper (the 1 input): wide at x=0, tapering to a point.
middle_input_width = 0.286      # um, input guide width at the left edge
middle_tip_width = 0.07         # um, tip where the center vanishes
middle_taper_length = 25.0      # um, adiabatic transfer length of the center guide
middle_center_offset = 0.016    # um, center guide axial offset (device is slightly off-axis)

# Outer arms (the 2 outputs): fine tips growing to full guide width.
arm_start_x = 3.0               # um, where the outer tips begin
arm_tip_width = 0.064           # um, outer-guide starting tip width
arm_width = 0.244               # um, output guide width
arm_taper_length = 23.2         # um, co-length over which tips grow to full width
top_couple_offset = 0.282       # um, top-arm center in the coupling region
bottom_couple_offset = 0.258    # um, bottom-arm center in the coupling region (below axis)
couple_straight_length = 0.8    # um, short co-propagation straight before fan-out

# Fan-out: S-bend the two guides apart to their final separation, then straight out.
sbend_length = 8.5              # um, fan-out S-bend length
output_offset = 0.731           # um, final half-separation of the two output ports
output_straight_length = 4.5    # um, straight output section to the right edge

# Path-length imbalance added to the TOP output arm (phase/split bias knob).
# Baseline 0 => balanced, symmetric 50/50 splitter.
delta_length = 0.0              # um

OUTPUT_GDS = "device.gds"


def _sbend_points(x0: float, y0: float, dx: float, dy: float, n: int = 160):
    """Raised-cosine S-bend centerline from (x0, y0) to (x0+dx, y0+dy)."""
    t = np.linspace(0.0, 1.0, n)
    x = x0 + dx * t
    y = y0 + dy * (0.5 - 0.5 * np.cos(np.pi * t))
    return np.column_stack([x, y])


def _arclength(pts: np.ndarray) -> float:
    return float(np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1)).sum())


# Output-arm spec: (name, coupling-region center, output-port center, extra length).
# The device is a balanced splitter; delta_length biases only the top arm.
def _arm_specs():
    return [
        ("top", +top_couple_offset, +output_offset, delta_length),
        ("bottom", -bottom_couple_offset, -output_offset, 0.0),
    ]


def _build(c: gf.Component) -> dict:
    """Add all geometry to c; return the two output-arm path lengths (um)."""
    # --- Central input taper: wide -> point, left edge at x=0 ---
    center_taper = gf.components.taper(
        length=middle_taper_length,
        width1=middle_input_width,
        width2=middle_tip_width,
        layer=LAYER,
    )
    c.add_ref(center_taper).move((0.0, middle_center_offset))

    x_taper_end = arm_start_x + arm_taper_length
    x_couple_end = x_taper_end + couple_straight_length
    x_sbend_end = x_couple_end + sbend_length

    arm_lengths = {}
    for name, y_couple, y_out, extra in _arm_specs():
        # Outer tip -> full width taper (the transfer region)
        arm_taper = gf.components.taper(
            length=arm_taper_length,
            width1=arm_tip_width,
            width2=arm_width,
            layer=LAYER,
        )
        c.add_ref(arm_taper).move((arm_start_x, y_couple))

        # Short co-propagation straight at full width before fanning out
        couple = gf.path.extrude(
            gf.path.straight(length=couple_straight_length), width=arm_width, layer=LAYER
        )
        c.add_ref(couple).move((x_taper_end, y_couple))

        # Fan-out S-bend: raised-cosine centerline, constant guide width
        sbend_pts = _sbend_points(x_couple_end, y_couple, sbend_length, y_out - y_couple)
        c.add_ref(gf.path.extrude(gf.Path(sbend_pts), width=arm_width, layer=LAYER))

        # Output straight to the right edge; top arm carries the delta_length bias
        straight = gf.path.extrude(
            gf.path.straight(length=output_straight_length + extra),
            width=arm_width,
            layer=LAYER,
        )
        c.add_ref(straight).move((x_sbend_end, y_out))

        # True path length of this arm, from its own path objects
        arm_lengths[name] = (
            arm_taper_length
            + couple_straight_length
            + _arclength(sbend_pts)
            + output_straight_length
            + extra
        )

    return arm_lengths


@gf.cell
def adiabatic_splitter() -> gf.Component:
    c = gf.Component()
    _build(c)
    return c


def _write_lengths(arm_lengths: dict) -> None:
    """Emit lengths.json (measurement contract): the two output-arm path lengths."""
    top, bottom = arm_lengths["top"], arm_lengths["bottom"]
    payload = {
        "arms": {"top": top, "bottom": bottom},
        "delta_length_um": abs(top - bottom),
    }
    Path("lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    comp = adiabatic_splitter()
    # Flatten before writing so the geometry lives in a real top-level cell rather
    # than only under kfactory's $$$CONTEXT_INFO$$$ metadata cell (which the
    # spec_optimization area/bbox readers skip). Silhouette is identical.
    flat = comp.copy()
    flat.flatten()
    flat.write_gds(OUTPUT_GDS)
    # Re-run the build off-cell to recover each arm's true path length for lengths.json.
    _write_lengths(_build(gf.Component()))
