"""The stencil rung's splitter, verbatim: gdsfactory's stock mmi1x2 with stubs.

Writes stencil_splitter.gds + splitter_meta.json (same tier-1 contract as the
primitives splitter) for the per-metric ladder comparison.
"""
import json
from pathlib import Path

import gdsfactory as gf

HERE = Path(__file__).parent

c = gf.Component("stencil_splitter_wrap")
mmi = c << gf.components.mmi1x2()  # the library cell, untouched
stub_in = c << gf.components.straight(length=5.0)
# fan the outputs apart before measuring: monitor planes must not span both
# guides (supermode projection corrupts per-port power — the negative-IL bug)
fan_top = c << gf.components.bend_s(size=(12.0, 2.2))
fan_bot = c << gf.components.bend_s(size=(12.0, -2.2))
stub_top = c << gf.components.straight(length=4.0)
stub_bot = c << gf.components.straight(length=4.0)
stub_in.connect("o2", mmi.ports["o1"])
fan_top.connect("o1", mmi.ports["o2"])
fan_bot.connect("o1", mmi.ports["o3"])
stub_top.connect("o1", fan_top.ports["o2"])
stub_bot.connect("o1", fan_bot.ports["o2"])

c.write_gds(HERE / "stencil_splitter.gds")

pin = stub_in.ports["o1"]
ptop = stub_top.ports["o2"]
pbot = stub_bot.ports["o2"]
meta = {
    "source": "gf.components.mmi1x2() stock cell + straight stubs "
    "(representation rule: library geometry untouched)",
    "port_positions": {
        "in": [round(pin.dcenter[0] + 1.0, 3), round(pin.dcenter[1], 3)],
        "out_top": [round(ptop.dcenter[0] - 1.0, 3), round(ptop.dcenter[1], 3)],
        "out_bot": [round(pbot.dcenter[0] - 1.0, 3), round(pbot.dcenter[1], 3)],
    },
}
(HERE / "splitter_meta.json").write_text(json.dumps(meta, indent=2))
print("bbox:", round(c.xsize, 2), "x", round(c.ysize, 2), "um; ports:", meta["port_positions"])
