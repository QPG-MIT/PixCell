"""
Measurement fixture for 400 nm TFLN strip: the device verbatim plus straight output stubs
so the two outputs are >= 5 um apart with >= 3 um single-mode stubs for the FDTD
mode monitors. Writes fixture_tfln400.gds and splitter_meta.json (port positions).
The fixture may exceed the device footprint budget; the DEVICE must not.
"""

import json
from pathlib import Path

import gdsfactory as gf

import device_tfln400 as D

LAYER = (1, 0)
FIXTURE_GDS = "fixture_tfln400.gds"
EXTRA_STUB = 6.0  # um, added to each output beyond the device stub for a clean monitor plane


def build_fixture():
    c = gf.Component()
    D._build(c)  # device geometry verbatim

    # Extend both outputs with a straight stub (device already fans to >= 5 um apart)
    for sgn in (+1.0, -1.0):
        y_out = sgn * D.output_offset
        stub = gf.path.extrude(
            gf.path.straight(length=EXTRA_STUB), width=D.arm_width, layer=LAYER
        )
        c.add_ref(stub).move((D.X_OUT_END, y_out))
    return c


if __name__ == "__main__":
    c = build_fixture()
    flat = c.copy()
    flat.flatten()
    flat.write_gds(FIXTURE_GDS)

    x_out = D.X_OUT_END + EXTRA_STUB - 1.0  # monitor plane 1 um inside the stub end
    meta = {
        "port_positions": {
            "in": [0.5, 0.0],
            "out_top": [round(x_out, 3), round(+D.output_offset, 3)],
            "out_bot": [round(x_out, 3), round(-D.output_offset, 3)],
        },
        "stack": "tfln400",
        "wg_width_um": D.arm_width,
        "output_center_to_center_um": round(2 * D.output_offset, 3),
        "note": "in port on the single-mode center input; out ports on the fanned-out stubs",
    }
    Path("splitter_meta.json").write_text(json.dumps(meta, indent=2))
    print("fixture written; ports:", meta["port_positions"])
