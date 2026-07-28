"""Adiabatic (mode-evolution) 1x2 power splitter — parametric primitives only.

Topology
--------
A three-waveguide adiabatic coupler followed by two S-bend fan-outs.

    x=0                x=coupler_start            x=center_tip           x=40
     |                        |                        |                  |
     |   ----------- outer arm (tip -> wide) ----------\\__ S-bend __------ o2
     |======= centre bus (wide -> tip) ================>
     |   ----------- outer arm (tip -> wide) ----------//‾‾ S-bend ‾‾------ o3

Light enters the wide centre bus, which has by far the highest effective index
at the coupler entrance, so the system's fundamental supermode is the centre
mode.  Along the coupler the centre guide is narrowed while the two outer guides
are widened; the effective indices cross, and the fundamental supermode becomes
the EVEN combination of the two outer-guide modes.  If the taper is slow
compared with the supermode beat length the field follows adiabatically and the
power ends up split 50/50 and in phase.  The split ratio is enforced by the
mirror symmetry of the structure, not by an interference length — which is what
makes this splitter broadband and fabrication-tolerant, at the cost of length.

Function knobs (top-level tunables below):
  arm_taper_length_um / center_taper_length_um : adiabaticity (the length knob)
  coupler_gap_um                               : inter-guide coupling strength
  wg_width_in / arm_tip_width_um               : which side of the index crossing
                                                 the device starts on
  center_tip_width_um                          : residual centre-guide power
  wg_width_out                                 : output single-mode width
  sbend_length_um / output_half_separation_um  : output routing / bend loss

gdsfactory 9.20.7, layer (1, 0).  Widths are snapped to the 2 nm grid required
by kfactory symmetric cross-sections.
"""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np

# --------------------------------------------------------------------------
# Tunables (top-level `name = value` — the parametric contract)
# --------------------------------------------------------------------------
layer = (1, 0)

# --- widths -----------------------------------------------------------------
wg_width_in = 0.270  # centre input bus width (um)
wg_width_out = 0.240  # each output arm width (um)
center_tip_width_um = 0.070  # blunt tip that terminates the centre taper (um)
arm_tip_width_um = 0.068  # blunt tip that starts each outer arm (um)

# --- coupler ----------------------------------------------------------------
coupler_gap_um = 0.0995  # centre-bus edge to arm edge at the coupler entrance
input_straight_um = 3.00  # bus-only lead-in before the coupler starts
center_taper_length_um = 22.03  # centre bus: wg_width_in -> center_tip_width_um
arm_taper_length_um = 22.60  # each arm: arm_tip_width_um -> wg_width_out

# --- output fan-out ---------------------------------------------------------
sbend_length_um = 10.67  # S-bend span along x
output_half_separation_um = 0.7290  # final output axis distance from y = 0
output_straight_um = 3.73  # straight run to the right edge

# Routing-only offset of the whole coupler assembly (centre bus + both arms)
# relative to the midline of the two output guides.  The coupler itself stays
# mirror-symmetric about its own axis -- which is what enforces the 50/50 split
# -- so this only makes the two fan-out S-bends travel slightly different
# vertical distances.  Reproduces the offset present in the source figure.
coupler_axis_offset_um = 0.011

# Figure-reproduction term, NOT a design parameter: in the source drawing the
# centre bus sits ~4 nm above the midline of the two outer arms.  The physical
# design value is 0 (the bus must be centred between the arms for a 50/50
# split); it is kept explicit and separate so it can be zeroed at retarget.
center_bus_offset_um = 0.004

sbend_npoints = 401  # centreline sampling of the cubic Bezier

# derived: centre-to-centre spacing between the bus and each arm, held constant
# through the whole coupler (the three centrelines are parallel).
arm_pitch_um = coupler_gap_um + 0.5 * (wg_width_in + arm_tip_width_um)


def _xs(width: float) -> gf.CrossSection:
    """A straight cross-section of the given width on the device layer."""
    return gf.cross_section.cross_section(width=width, layer=layer)


def _sbend_path(length: float, offset: float, npoints: int) -> gf.Path:
    """Cubic-Bezier ('smoothstep') S-bend centreline: zero slope at both ends.

    P0=(0,0)  P1=(L/2,0)  P2=(L/2,dY)  P3=(L,dY)
    """
    s = np.linspace(0.0, 1.0, npoints)
    x = 1.5 * length * s * (1.0 - s) + length * s**3
    y = offset * (3.0 * s**2 - 2.0 * s**3)
    return gf.Path(np.column_stack([x, y]))


@gf.cell
def adiabatic_splitter_1x2() -> gf.Component:
    c = gf.Component()

    xs_in = _xs(wg_width_in)
    xs_center_tip = _xs(center_tip_width_um)
    xs_arm_tip = _xs(arm_tip_width_um)
    xs_out = _xs(wg_width_out)

    # ---- centre bus: straight lead-in, then the down-taper to a blunt tip ---
    lead = c.add_ref(gf.path.extrude(gf.path.straight(length=input_straight_um), xs_in))
    lead.dmovey(coupler_axis_offset_um + center_bus_offset_um)

    center_taper = gf.path.extrude_transition(
        gf.path.straight(length=center_taper_length_um),
        gf.path.transition(xs_in, xs_center_tip, width_type="linear"),
    )
    ct = c.add_ref(center_taper)
    ct.dmovex(input_straight_um)
    ct.dmovey(coupler_axis_offset_um + center_bus_offset_um)

    # ---- the two outer arms (mirror images about y = 0) --------------------
    arm_taper = gf.path.extrude_transition(
        gf.path.straight(length=arm_taper_length_um),
        gf.path.transition(xs_arm_tip, xs_out, width_type="linear"),
    )
    out_straight = gf.path.extrude(gf.path.straight(length=output_straight_um), xs_out)

    x_bend_start = input_straight_um + arm_taper_length_um
    x_bend_end = x_bend_start + sbend_length_um

    arm_paths: dict[str, float] = {}
    for name, sign in (("top", +1.0), ("bottom", -1.0)):
        y0 = sign * arm_pitch_um + coupler_axis_offset_um
        y1 = sign * output_half_separation_um

        t = c.add_ref(arm_taper)
        t.dmovex(input_straight_um)
        t.dmovey(y0)

        bend_path = _sbend_path(sbend_length_um, y1 - y0, sbend_npoints)
        b = c.add_ref(gf.path.extrude(bend_path, xs_out))
        b.dmovex(x_bend_start)
        b.dmovey(y0)

        s = c.add_ref(out_straight)
        s.dmovex(x_bend_end)
        s.dmovey(y1)

        arm_paths[name] = float(
            arm_taper_length_um + bend_path.length() + output_straight_um
        )

    c.add_port(
        "o1",
        center=(0.0, coupler_axis_offset_um + center_bus_offset_um),
        width=wg_width_in,
        orientation=180,
        layer=layer,
    )
    c.add_port(
        "o2",
        center=(x_bend_end + output_straight_um, output_half_separation_um),
        width=wg_width_out,
        orientation=0,
        layer=layer,
    )
    c.add_port(
        "o3",
        center=(x_bend_end + output_straight_um, -output_half_separation_um),
        width=wg_width_out,
        orientation=0,
        layer=layer,
    )

    c.info["arm_length_top_um"] = arm_paths["top"]
    c.info["arm_length_bottom_um"] = arm_paths["bottom"]
    return c


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    component = adiabatic_splitter_1x2()

    # Write a FLAT, plain-Component GDS.  kfactory emits a $$$CONTEXT_INFO$$$
    # metadata cell that REFERENCES any @gf.cell-registered top cell; that makes
    # the real cell non-top-level, so a reader iterating top_level() and skipping
    # $$$ cells (homi.spec_optimization._layer_area does exactly that) measures
    # zero area.  Re-hosting the geometry in a plain gf.Component and flattening
    # keeps the parametric cell hierarchical while making the artifact readable.
    # Geometry is unchanged.
    flat = gf.Component("adiabatic_splitter_1x2_flat")
    flat.add_ref(component)
    flat.flatten()
    gds_path = out_dir / "device.gds"
    flat.write_gds(gds_path)

    bbox = component.dbbox()
    (out_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {
                    "top": component.info["arm_length_top_um"],
                    "bottom": component.info["arm_length_bottom_um"],
                },
                # contract convention: abs difference of the two arm paths.
                # For a 1x2 splitter this is ~0 by design (the two output arms
                # are nominally identical); the residual 2 nm is the small
                # difference in S-bend travel caused by coupler_axis_offset_um.
                "delta_length_um": abs(
                    float(component.info["arm_length_top_um"])
                    - float(component.info["arm_length_bottom_um"])
                ),
                "coupler_length_um": float(arm_taper_length_um),
                "arm_pitch_um": float(arm_pitch_um),
                "bbox_um": [bbox.left, bbox.bottom, bbox.right, bbox.top],
            },
            indent=2,
        )
    )
    print(f"wrote {gds_path}")
    print(f"bbox um: {bbox}")
