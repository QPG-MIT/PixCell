"""
Measurement fixture for 220 nm SOI strip (round-1 BEST device).

The device verbatim plus straight output stubs so the two outputs are >= 5 um
apart with single-mode stubs for the FDTD mode monitors. This matches the fixture
that produced the valid round-1 measurement T=0.928, balance 0.500 (soi220's best
within the cap). The fixture may exceed the device budget; the DEVICE must not.
"""

import json
from pathlib import Path

import gdsfactory as gf

import device_soi220 as D

LAYER = (1, 0)
FIXTURE_GDS = "fixture_soi220.gds"
EXTRA_STUB = 6.0  # um, added to each output beyond the device stub for a clean monitor plane


def build_fixture():
    c = gf.Component()
    D._build(c)  # device geometry verbatim
    for sgn in (+1.0, -1.0):
        stub = gf.path.extrude(
            gf.path.straight(length=EXTRA_STUB), width=D.arm_width, layer=LAYER
        )
        c.add_ref(stub).move((D.X_OUT_END, sgn * D.output_offset))
    return c


if __name__ == "__main__":
    c = build_fixture()
    flat = c.copy()
    flat.flatten()
    flat.write_gds(FIXTURE_GDS)

    x_out = D.X_OUT_END + EXTRA_STUB - 1.0
    meta = {
        "port_positions": {
            "in": [0.5, 0.0],
            "out_top": [round(x_out, 3), round(+D.output_offset, 3)],
            "out_bot": [round(x_out, 3), round(-D.output_offset, 3)],
        },
        "stack": "soi220",
        "wg_width_um": D.arm_width,
        "output_center_to_center_um": round(2 * D.output_offset, 3),
        "note": "round-1 best device (T=0.928); in on center input, out on fanned-out stubs 6um apart",
    }
    Path("splitter_meta.json").write_text(json.dumps(meta, indent=2))
    print("fixture written; ports:", meta["port_positions"])
