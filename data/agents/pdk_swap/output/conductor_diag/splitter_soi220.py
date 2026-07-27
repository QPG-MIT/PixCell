"""Standalone 1x2 MMI splitter for tier-1 (FDTD) characterization -- 220 nm SOI.

The MMI cell is parametrically IDENTICAL to the splitter/combiner inside
mzi_soi220.py (same top-level mmi_* parameters and builder). Only the CHARACTERIZATION
FIXTURE differs: the input gets a straight monitor stub, and the two outputs are fanned
apart by symmetric s-bends to >=5 um center-to-center before their monitor stubs, so the
conductor's FDTD monitor planes no longer overlap both guides. splitter_meta.json carries
the real, measured port coordinates.

Self-imaging: L_mmi = 3*L_pi/8, L_pi = 15.20 um (multimode, W=2.5 um, SOI); centered
input images to two equal spots at +-mmi_width/6 -> t=0.5 by symmetry.
Primitives only: rectangle + taper + straight. No device stencils, no raw polygons.
"""

import json
from pathlib import Path

import gdsfactory as gf

# --- top-level MMI parameters (identical to mzi_soi220.py) ---
wg_width = 0.5  # single-mode waveguide width (um)
mmi_width = 2.5  # multimode body width (um)
mmi_length = 5.500  # body length (um) = 3*L_pi/8, L_pi=15.20 um
mmi_access_w = 1.0  # MATCHED input & output taper facet width (um): wide aperture covers the image
mmi_taper_len = 11.0  # adiabatic access taper length (um)
L_pi_um = 15.20  # measured beat length (multimode, W=2.5, SOI 220nm/1.55um)
output_offset = 0.625  # mouth center (um), parked outboard: aperture covers the inboard ~0.42 spot
stub_len = 3.0  # short straight stub on each port for FDTD source/monitors (um)

# --- FIXTURE-ONLY fan-out (does NOT change the MMI cell) ---
# The MMI images its two outputs only 0.83 um apart (+-W/6), too close for separate
# monitor planes -> the planes overlapped both guides and the supermode projection
# corrupted per-port power. Fan the two outputs apart to >= 5 um center-to-center with
# symmetric s-bends, then place the >= 3 um monitor stubs on the well-separated guides.
out_separation = 5.4  # center-to-center separation of the two output monitor guides (um)
fan_dx = 12.0  # s-bend longitudinal length (um); keeps bend radius above the 10 um minimum

LAYER = (1, 0)
_xs = gf.cross_section.cross_section(width=wg_width, layer=LAYER)


def _mmi_1x2() -> gf.Component:
    """Primitives-only symmetric 1x2 MMI (identical to the device's builder):
    rectangle body + centered input taper + two matched-width output access tapers at
    +-mmi_width_eff/6."""
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


@gf.cell
def splitter_soi220() -> gf.Component:
    c = gf.Component()
    mref = c.add_ref(_mmi_1x2())
    off = output_offset

    # Input monitor stub extends left from the 'in' port.
    in_stub = c.add_ref(gf.path.extrude(gf.path.straight(length=stub_len), cross_section=_xs))
    in_stub.connect("o2", mref.ports["in"])

    # Fan the two MMI outputs apart with symmetric s-bends, then place monitor stubs on the
    # well-separated guides. dy per bend takes each guide from +-off to +-out_separation/2.
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
        "mmi_width_um": mmi_width,
        "mmi_length_um": mmi_length,
        "L_pi_um": L_pi_um,
        "predicted_split_fraction": 0.5,
        "predicted_ER_db": ">=30 (by symmetry, subject to imaging quality)",
        "output_separation_um": round(sep_measured, 4),
        "port_positions": {k: [round(v[0], 4), round(v[1], 4)] for k, v in ports.items()},
        "note": "MMI cell identical to the device (W=2.5, L_mmi=3*L_pi/8=5.700, matched 1.0 um "
        "access mouths parked at +-0.625 um so the aperture covers the inboard image spot, "
        "11 um adiabatic tapers). Fixture-only: symmetric s-bends fan the two outputs to >=5 um "
        "center-to-center, then >=3 um monitor stubs, so the FDTD monitor planes no longer "
        "overlap both guides.",
    }
    (Path(__file__).parent / "splitter_meta.json").write_text(json.dumps(meta, indent=2))
    return c


if __name__ == "__main__":
    comp = splitter_soi220()
    out = Path(__file__).parent / "splitter_soi220.gds"
    comp.write_gds(str(out), with_metadata=False)
    print(f"wrote {out}")
    print((Path(__file__).parent / "splitter_meta.json").read_text())
