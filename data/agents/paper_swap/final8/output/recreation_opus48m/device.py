"""
Recreation of experiments/paper_swap/final8 device.

Device (from the B&W figure): a symmetric multi-rail / waveguide-array
(supermode) coupler.  Transverse cross-section, top->bottom, mirror-symmetric
about the mid-line y=W/2:

    [array A : n_wires thin guides] | [rail B : one wide slab]
    [array C : n_wires thin guides]  (centered, runs the FULL length)
    [rail D : one wide slab] | [array E : n_wires thin guides]

The centre array C runs straight the whole length.  The two OUTER bundles
(rail B + array A above, rail D + array E below) run parallel to C over the
central COUPLING region, then adiabatically S-bend to the top/bottom edge and
exit at each end.

Everything is built from primitives only: gf.Path straights + a cosine S-bend
path, extruded on layer (1, 0).  No gf.components device stencils, no raw
polygons.  Geometry lives in the calibrated frame (x: 0..120 um, y: 0..4 um)
that compare_absolute renders with independent x/y scales.
"""

import json
import numpy as np
import gdsfactory as gf

# ----------------------------------------------------------------------------
# Top-level tunables (the parametric contract).  Function knobs are top-level.
# ----------------------------------------------------------------------------
footprint_length_um = 120.0   # device length L (propagation axis)
footprint_width_um = 4.0      # device width W (transverse axis)

n_wires = 5                   # thin guides per array (A, C, E)
wire_width = 0.068            # FUNCTION KNOB: transverse guide width (sets coupling)
wire_pitch = 0.10             # FUNCTION KNOB: array period (supermode splitting)
slab_width = 0.468            # FUNCTION KNOB: wide-rail (B, D) width
gap = 0.031                   # FUNCTION KNOB: edge-to-edge rail/array coupling gap

array_offset = 1.0            # transverse offset of arrays A/E from centre (C at W/2)
slab_offset = 0.5             # transverse offset of rails B/D from centre

coupling_length = 99.0        # FUNCTION KNOB: straight parallel-run (power-transfer) length
flare_length = 8.0            # FUNCTION KNOB: adiabatic access-bend length at each end
flare_overshoot = 0.45        # how far the outer bundle overshoots past the edge (clipped)

delta_length = 0.0            # FUNCTION KNOB: outer-arm path-length imbalance (Phase-B FSR
                              # knob).  0 in the figure => balanced/symmetric.

LAYER = (1, 0)


def _straight(component, length, width, x_left, y_center):
    """A horizontal bar (gf.Path straight extruded) placed by its left edge / y-centre."""
    if length <= 0:
        return
    p = gf.path.straight(length=length)
    xs = gf.cross_section.cross_section(width=width, layer=LAYER)
    ref = component.add_ref(p.extrude(xs))
    ref.dmove((x_left, y_center))  # straight is centred on y=0 starting at x=0
    return ref


def _cosine_sbend_points(x0, y0, x1, y1, n=60):
    xs = np.linspace(x0, x1, n)
    t = (xs - x0) / (x1 - x0)
    ys = y0 + (y1 - y0) * (0.5 - 0.5 * np.cos(np.pi * t))
    return np.column_stack([xs, ys])


def _flare(component, x_junction, x_tip, y_center_straight, y_center_tip, env_w):
    """Solid bent band (extruded cosine S-bend) modelling the merged outer bundle
    where it bends off the chip edge; internal gaps have closed by there."""
    pts = _cosine_sbend_points(x_junction, y_center_straight, x_tip, y_center_tip)
    path = gf.Path(pts)
    xs = gf.cross_section.cross_section(width=env_w, layer=LAYER)
    component.add_ref(path.extrude(xs))


@gf.cell
def device() -> gf.Component:
    c = gf.Component()
    L = footprint_length_um
    W = footprint_width_um
    cy = W / 2.0

    half = (n_wires - 1) / 2.0
    # transverse centres
    cA = cy - array_offset
    cC = cy
    cE = cy + array_offset
    cB = cy - slab_offset
    cD = cy + slab_offset

    # straight coupling region x-range (centred)
    x0 = (L - coupling_length) / 2.0
    x1 = x0 + coupling_length

    def array(center, xL, length):
        for i in range(n_wires):
            y = center + (i - half) * wire_pitch
            _straight(c, length, wire_width, xL, y)

    # --- centre array C: full length ---
    array(cC, 0.0, L)

    # --- top outer bundle (array A + rail B), straight coupling section ---
    array(cA, x0, coupling_length)
    _straight(c, coupling_length, slab_width, x0, cB)

    # --- bottom outer bundle (rail D + array E), straight coupling section ---
    #     bottom arm carries the delta_length imbalance (extended on the right)
    array(cE, x0, coupling_length + delta_length)
    _straight(c, coupling_length + delta_length, slab_width, x0, cD)

    # --- outer-bundle envelopes (for the flares) ---
    top_env_top = cA - half * wire_pitch - wire_width / 2.0   # outer edge (toward y=0)
    top_env_bot = cB + slab_width / 2.0                        # inner edge (toward centre)
    top_env_c = (top_env_top + top_env_bot) / 2.0
    top_env_w = top_env_bot - top_env_top

    bot_env_bot = cE + half * wire_pitch + wire_width / 2.0    # outer edge (toward y=W)
    bot_env_top = cD - slab_width / 2.0
    bot_env_c = (bot_env_top + bot_env_bot) / 2.0
    bot_env_w = bot_env_bot - bot_env_top

    # --- flares: top bundle bends toward y=0 (overshoot < 0), bottom toward y=W ---
    top_tip_y = -flare_overshoot
    bot_tip_y = W + flare_overshoot
    # left flares
    _flare(c, x0, x0 - flare_length, top_env_c, top_tip_y, top_env_w)
    _flare(c, x0, x0 - flare_length, bot_env_c, bot_tip_y, bot_env_w)
    # right flares
    _flare(c, x1, x1 + flare_length, top_env_c, top_tip_y, top_env_w)
    _flare(c, x1 + delta_length, x1 + delta_length + flare_length, bot_env_c, bot_tip_y, bot_env_w)

    return c


def _write_lengths(gds_dir="."):
    """Self-measured arm lengths for the measurement contract (measured_delta_length).

    The two 'arms' are the two OUTER coupled bundles' straight parallel-run
    lengths, computed from the same parameters that place their geometry:
    top = coupling_length, bottom = coupling_length + delta_length.
    delta_length_um is their difference (0 in the balanced figure).
    """
    arm_top = coupling_length
    arm_bottom = coupling_length + delta_length
    payload = {
        "arms": {"outer_top": arm_top, "outer_bottom": arm_bottom},
        "delta_length_um": abs(arm_bottom - arm_top),
    }
    from pathlib import Path
    Path(gds_dir, "lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    comp = device()
    # with_metadata=False: avoid kfactory's $$$CONTEXT_INFO$$$ cell, which would
    # reference the device cell and demote it below top-level (the measurement
    # contract's _layer_area skips $$$ cells and would then read zero area).
    comp.write_gds("device.gds", with_metadata=False)
    _write_lengths(".")
    print("wrote device.gds; bbox um:", comp.bbox())
