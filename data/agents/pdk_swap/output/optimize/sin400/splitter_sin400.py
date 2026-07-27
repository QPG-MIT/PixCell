"""Standalone 1x2 MMI splitter for tier-1 (FDTD) characterization -- 400 nm SiN strip.

Per-stack DERIVATION (not a transplant): the SOI saga's recipe re-derived on SiN.
  * Body width: SiN is weakly confined (n 1.996/1.444), so the same modal picture needs a
    wider body. W=4.0 um is the smallest clearly-multimode body (beat length exists, fewest
    modes -> cleanest imaging, the SOI 'wider imaged worse' lesson).
  * Imaging length: L_pi = 27.23 um (multimode solve on stacks/sin400.json, W=4.0). Analytic
    self-image L = 3*L_pi/8 = 10.211 um, then the SOI empirical calibration (tier-0 3*L_pi/8
    ran ~4% long: 5.70 um theory vs 5.50 um measured optimal) scale 5.50/5.70 = 0.9649 ->
    L_mmi = 9.853 um.
  * Access (SOI final recipe): matched WIDE mouths (1.6 um, 1.6x the 1.0 um SiN single mode)
    parked OUTBOARD at +-1.0 um so their aperture 0.20..1.80 covers the inboard image spot
    (~W/6 = 0.667 um), gap 2*1.0-1.6 = 0.40 um (>= 0.2 brief, >= 0.4 stack min_feature), and
    LONG adiabatic tapers (15 um, slope ~0.04) 1.0<->1.6 um.

Fixture: symmetric fan-out s-bends separate the two outputs to >=5 um center-to-center, then
straight monitor stubs, so FDTD monitor planes isolate each guide. All cross-sections 1.0 um.
Primitives only: rectangle + taper + straight + bend_s. No device stencils, no raw polygons.
"""

import json
from pathlib import Path

import gdsfactory as gf

# --- top-level MMI parameters (per-stack derived for SiN 400 nm) ---
wg_width = 1.0  # SiN single-mode waveguide width (um)
mmi_width = 4.0  # multimode body width (um); smallest clean multimode body on SiN
mmi_length = 9.853  # body length (um) = 3*L_pi/8 * 0.9649 (SOI empirical calibration)
mmi_access_w = 1.6  # MATCHED input & output taper facet width (um): wide aperture covers the image
mmi_taper_len = 15.0  # adiabatic access taper length (um): 1.0<->1.6 over 15 um, slope ~0.04
L_pi_um = 27.23  # measured beat length (multimode, W=4.0, SiN 400nm/1.55um)
output_offset = 1.0  # mouth center (um), parked outboard: aperture 0.20..1.80 covers inboard spot
stub_len = 3.0  # straight monitor stub on each port (um)

# --- fixture-only fan-out (does NOT change the MMI cell) ---
out_separation = 6.0  # center-to-center separation of the two output monitor guides (um)
fan_dx = 14.0  # s-bend longitudinal length (um); keeps bend radius above the 10 um minimum

LAYER = (1, 0)
_xs = gf.cross_section.cross_section(width=wg_width, layer=LAYER)


def _mmi_1x2() -> gf.Component:
    """Primitives-only symmetric 1x2 MMI: rectangle body + centered input taper + two output
    access tapers whose wide mouths (mmi_access_w) are parked at +-output_offset so the aperture
    covers the inboard image spot. Ports: 'in' (left), 'out_top'/'out_bot' (right)."""
    L = mmi_length
    m = gf.Component()
    m.add_ref(gf.components.rectangle(size=(L, mmi_width), layer=LAYER, centered=True))
    tin = m.add_ref(
        gf.components.taper(length=mmi_taper_len, width1=wg_width, width2=mmi_access_w, layer=LAYER)
    )
    tin.move((-L / 2 - mmi_taper_len, 0.0))
    m.add_port(
        "in", center=(-L / 2 - mmi_taper_len, 0.0), width=wg_width, orientation=180, layer=LAYER
    )
    for name, sgn in (("out_top", +1), ("out_bot", -1)):
        to = m.add_ref(
            gf.components.taper(
                length=mmi_taper_len, width1=mmi_access_w, width2=wg_width, layer=LAYER
            )
        )
        to.move((L / 2, sgn * output_offset))
        m.add_port(
            name,
            center=(L / 2 + mmi_taper_len, sgn * output_offset),
            width=wg_width,
            orientation=0,
            layer=LAYER,
        )
    return m


# DRC: output-mouth gap respects the min gap.
_out_gap = 2.0 * output_offset - mmi_access_w
assert _out_gap >= 0.2, f"MMI output-guide gap {_out_gap:.3f} um < 0.2 um"


@gf.cell
def splitter_sin400() -> gf.Component:
    c = gf.Component()
    mref = c.add_ref(_mmi_1x2())
    off = output_offset

    in_stub = c.add_ref(gf.path.extrude(gf.path.straight(length=stub_len), cross_section=_xs))
    in_stub.connect("o2", mref.ports["in"])

    fan_dy = out_separation / 2.0 - off
    ports = {"in": list(in_stub.ports["o1"].center)}
    for name, sgn in (("out_top", +1), ("out_bot", -1)):
        bend = c.add_ref(gf.components.bend_s(size=(fan_dx, sgn * fan_dy), cross_section=_xs))
        bend.connect("o1", mref.ports[name])
        stub = c.add_ref(gf.path.extrude(gf.path.straight(length=stub_len), cross_section=_xs))
        stub.connect("o1", bend.ports["o2"])
        ports[name] = list(stub.ports["o2"].center)

    sep_measured = abs(ports["out_top"][1] - ports["out_bot"][1])
    meta = {
        "stack": "sin400",
        "mmi_width_um": mmi_width,
        "mmi_length_um": mmi_length,
        "L_pi_um": L_pi_um,
        "predicted_split_fraction": 0.5,
        "predicted_ER_db": ">=30 (by symmetry, subject to imaging quality)",
        "output_separation_um": round(sep_measured, 4),
        "port_positions": {k: [round(v[0], 4), round(v[1], 4)] for k, v in ports.items()},
        "note": "Per-stack derived (NOT transplanted). W=4.0, L_mmi=3*L_pi/8*0.9649=9.853 um "
        "(L_pi=27.23; SOI empirical length calibration applied), matched 1.6 um mouths parked at "
        "+-1.0 um (gap 0.40 um), 15 um adiabatic tapers, wg 1.0 um. Fixture-only: s-bend fan-out "
        "to >=5 um center-to-center + monitor stubs so FDTD planes isolate each guide.",
    }
    (Path(__file__).parent / "splitter_meta.json").write_text(json.dumps(meta, indent=2))
    return c


if __name__ == "__main__":
    comp = splitter_sin400()
    out = Path(__file__).parent / "splitter_sin400.gds"
    comp.write_gds(str(out), with_metadata=False)
    print(f"wrote {out}")
    print((Path(__file__).parent / "splitter_meta.json").read_text())
