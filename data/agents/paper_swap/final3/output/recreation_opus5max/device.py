"""Adiabatic 2x2 directional coupler (mode-evolution 3 dB splitter).

Recreated from data/agents/paper_swap/final3/device_bw.png at the calibrated
absolute scale (footprint 120 x 4 um).

Physics
-------
Two waveguides are brought to a fixed sub-wavelength gap and then have their
widths counter-tapered: the arm that starts wide narrows, the arm that starts
narrow widens, with the SUM of the two widths held roughly constant so the gap
and both centrelines stay fixed.  Light launched into the wide guide starts as
(almost) the pure even supermode of the pair; removing the width asymmetry
adiabatically keeps it in that local even supermode, which at the symmetric
output is an equal in-phase superposition of the two guide modes -> 50/50
splitting.

The splitting ratio is therefore set by the *end* asymmetry
(``w_wide_end_um`` vs ``w_narrow_end_um``), not by a resonant length, which is
what makes the device broadband and fabrication tolerant.

Primitives only: gf.Path + extrude / extrude_transition, gf.components.taper,
@gf.cell assembly.
"""

from __future__ import annotations

import numpy as np
import gdsfactory as gf

# --------------------------------------------------------------------------
# Tunables (top-level, JEE-substitutable).  Function knobs first.
# --------------------------------------------------------------------------

# --- coupler function knobs -------------------------------------------------
coupler_gap_um = 0.1531         # edge-to-edge gap in the interaction region
coupling_length_um = 50.611     # adiabatic interaction (mode-evolution) length
w_wide_start_um = 0.424         # wide arm width entering the interaction region
w_narrow_start_um = 0.188       # narrow arm width entering the interaction region
w_wide_end_um = 0.314           # wide arm width leaving  the interaction region
w_narrow_end_um = 0.288         # narrow arm width leaving the interaction region

# --- launch / access knobs --------------------------------------------------
wg_width_um = 0.304             # single-mode bus width (platform-set)
input_taper_length_um = 9.513   # length over which the launch asymmetry is built
sbend_in_length_um = 17.720     # input access S-bend length
sbend_out_length_um = 19.300    # output access S-bend length
port_pitch_in_um = 3.4411       # input  bus centre-to-centre separation
port_pitch_out_um = 3.6640      # output bus centre-to-centre separation
sbend_in_exponent = 3.0         # input  access-bend profile: slope ~ sin^n(pi t)
sbend_out_exponent = 2.6        # output access-bend profile: slope ~ sin^n(pi t)

# --- straight lead-ins (layout, footprint-setting) --------------------------
input_straight_um = 7.020
output_straight_um = 15.836

# --- as-drawn residuals of the source figure (layout only) ------------------
# The figure is symmetric about its own mid-line only to ~2 px at the calibrated
# transverse scale.  These carry that residual; a clean design would set both
# offsets to 0 and both output buses to wg_width_um.
input_axis_offset_um = 0.0112   # input bus pair axis, relative to the frame centre
coupler_axis_offset_um = -0.0114  # interaction-region axis, same reference
w_port_top_um = 0.306           # top    output bus width as drawn
w_port_bot_um = 0.298           # bottom output bus width as drawn

# --- fabrication / meshing --------------------------------------------------
layer = (1, 0)
n_bend_points = 401


# --------------------------------------------------------------------------
# Primitive builders
# --------------------------------------------------------------------------

def _straight_path(x_start: float, x_stop: float, y: float) -> gf.Path:
    """Axial straight centreline as a gf.Path in absolute coordinates."""
    return gf.Path(np.array([[x_start, y], [x_stop, y]], dtype=float))


def _sbend_path(x_start: float, x_stop: float, y_start: float, y_stop: float,
                exponent: float) -> gf.Path:
    """S-bend centreline whose SLOPE follows sin^n(pi t).

    n = 1 is the raised-cosine S-bend; larger n concentrates the turn into the
    middle of the span (flatter approach, steeper crossing), which is what the
    source figure shows.  Slope and curvature both vanish at either end for
    n >= 2, so the bend joins the straights without a curvature step.
    """
    t = np.linspace(0.0, 1.0, n_bend_points)
    slope = np.sin(np.pi * t) ** exponent
    frac = np.concatenate([[0.0], np.cumsum(0.5 * (slope[1:] + slope[:-1]))])
    frac /= frac[-1]
    x = x_start + (x_stop - x_start) * t
    y = y_start + (y_stop - y_start) * frac
    return gf.Path(np.column_stack([x, y]))


def _extrude_tapered(p: gf.Path, width1: float, width2: float) -> gf.Component:
    """Extrude a path with a linear width transition (a tapered bend)."""
    return gf.path.extrude_transition(
        p,
        gf.path.transition(
            gf.cross_section.cross_section(width=width1, layer=layer),
            gf.cross_section.cross_section(width=width2, layer=layer),
            width_type="linear",
        ),
    )


def _add_taper(c: gf.Component, x_start: float, length: float, y: float,
               width1: float, width2: float) -> None:
    """Linear width transition on the axis y, spanning [x_start, x_start+length]."""
    ref = c.add_ref(
        gf.components.taper(length=length, width1=width1, width2=width2, layer=layer)
    )
    ref.dmove((x_start, y))


def _add_arm(c: gf.Component, sign: float, w_start: float, w_end: float,
             w_port: float) -> dict[str, float]:
    """One arm of the coupler.  ``sign`` = +1 for the top arm, -1 for the bottom arm.

    Width trajectory: wg_width -> w_start (launch taper), held constant through the
    access bend, then w_start -> w_end across the interaction region, then relaxed
    back to the output bus width through the exit bend.

    Returns the arm's centreline lengths, measured from the gf.Path objects.
    """
    # coupler centreline half-pitch: half the gap plus half of each entering width
    half_pitch_c = 0.5 * (coupler_gap_um + 0.5 * (w_wide_start_um + w_narrow_start_um))

    y_in = sign * 0.5 * port_pitch_in_um + input_axis_offset_um
    y_c = sign * half_pitch_c + coupler_axis_offset_um
    y_out = sign * 0.5 * port_pitch_out_um

    x0 = 0.0
    x1 = x0 + input_straight_um
    x2 = x1 + input_taper_length_um
    x3 = x2 + sbend_in_length_um
    x4 = x3 + coupling_length_um
    x5 = x4 + sbend_out_length_um
    x6 = x5 + output_straight_um

    # every segment's centreline is a gf.Path, so the arm length below is measured,
    # never hand-entered
    p_bus_in = _straight_path(x0, x1, y_in)
    p_taper_in = _straight_path(x1, x2, y_in)
    p_sbend_in = _sbend_path(x2, x3, y_in, y_c, sbend_in_exponent)
    p_interact = _straight_path(x3, x4, y_c)
    p_sbend_out = _sbend_path(x4, x5, y_c, y_out, sbend_out_exponent)
    p_bus_out = _straight_path(x5, x6, y_out)

    # input bus
    c.add_ref(gf.path.extrude(p_bus_in, layer=layer, width=wg_width_um))
    # launch taper: build the width asymmetry that selects the even supermode
    _add_taper(c, x1, input_taper_length_um, y_in, wg_width_um, w_start)
    # access S-bend down to the interaction gap (constant width)
    c.add_ref(gf.path.extrude(p_sbend_in, layer=layer, width=w_start))
    # interaction region: counter-taper (this is the mode-evolution section)
    _add_taper(c, x3, coupling_length_um, y_c, w_start, w_end)
    # exit S-bend, relaxing back to the output bus width
    c.add_ref(_extrude_tapered(p_sbend_out, w_end, w_port))
    # output bus
    c.add_ref(gf.path.extrude(p_bus_out, layer=layer, width=w_port))

    segments = (p_bus_in, p_taper_in, p_sbend_in, p_interact, p_sbend_out, p_bus_out)
    return {
        "total": float(sum(p.length() for p in segments)),
        "interaction": float(p_interact.length()),
        "sbend_in": float(p_sbend_in.length()),
        "sbend_out": float(p_sbend_out.length()),
    }


ARM_LENGTHS: dict[str, dict[str, float]] = {}


@gf.cell
def adiabatic_coupler() -> gf.Component:
    """Assemble the two counter-tapered arms."""
    c = gf.Component()
    ARM_LENGTHS["top"] = _add_arm(c, +1.0, w_wide_start_um, w_wide_end_um, w_port_top_um)
    ARM_LENGTHS["bottom"] = _add_arm(c, -1.0, w_narrow_start_um, w_narrow_end_um,
                                     w_port_bot_um)
    return c


if __name__ == "__main__":
    import json

    component = adiabatic_coupler()
    bbox = component.dbbox()
    print(f"bbox um: {bbox.width():.3f} x {bbox.height():.3f}")
    print(f"coupler gap um: {coupler_gap_um}")
    # with_metadata=False suppresses kfactory's $$$CONTEXT_INFO$$$ wrapper cell, which
    # otherwise becomes the GDS's only top-level cell and hides the geometry from
    # top-level readers (homi.spec_optimization._layer_area).
    component.write_gds("device.gds", with_metadata=False)

    top, bot = ARM_LENGTHS["top"], ARM_LENGTHS["bottom"]
    with open("lengths.json", "w") as fh:
        json.dump(
            {
                "arms": {"top": top["total"], "bottom": bot["total"]},
                "delta_length_um": abs(top["total"] - bot["total"]),
                "interaction_length_um": 0.5 * (top["interaction"] + bot["interaction"]),
                "note": (
                    "A 2x2 adiabatic coupler is length-BALANCED by construction, so the "
                    "MZI-shaped delta_length_um is ~0 and does not respond to any knob. "
                    "The knob-tracked optical length of this topology is "
                    "interaction_length_um (= coupling_length_um)."
                ),
            },
            fh,
            indent=2,
        )
    print(f"arm lengths um: top={top['total']:.4f} bottom={bot['total']:.4f}")
    print(f"interaction length um: {0.5*(top['interaction']+bot['interaction']):.4f}")
