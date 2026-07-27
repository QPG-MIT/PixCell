"""The frozen-dimensions transplant test: stock mmi1x2 body on the SiN stack.

As-shipped MMI body (2.5 x 5.5 um — tuned for 220 nm SOI), with only the
access waveguides width-adapted to the SiN platform (1.0 um strip), which is
the fair 'just use the PDK cell on another stack' transplant. Tier-0 predicts
the imaging point on SiN sits at 4.31 um — the frozen 5.5 um body is ~28% off.

Writes stencil_splitter.gds + splitter_meta.json (tier-1 contract).
"""
import json
from pathlib import Path

import gdsfactory as gf

HERE = Path(__file__).parent
XS = gf.cross_section.strip(width=1.0)  # SiN single-mode width

c = gf.Component("stencil_splitter_sin_transplant")
mmi = c << gf.components.mmi1x2(cross_section=XS)  # frozen body dims, adapted access
stub_in = c << gf.components.straight(length=5.0, cross_section=XS)
fan_top = c << gf.components.bend_s(size=(12.0, 2.2), cross_section=XS)
fan_bot = c << gf.components.bend_s(size=(12.0, -2.2), cross_section=XS)
stub_top = c << gf.components.straight(length=4.0, cross_section=XS)
stub_bot = c << gf.components.straight(length=4.0, cross_section=XS)
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
    "source": "stock gf.components.mmi1x2 body (2.5x5.5, SOI-tuned) transplanted to "
    "sin400 with width-adapted access — the frozen-craft transfer test",
    "port_positions": {
        "in": [round(pin.dcenter[0] + 1.0, 3), round(pin.dcenter[1], 3)],
        "out_top": [round(ptop.dcenter[0] - 1.0, 3), round(ptop.dcenter[1], 3)],
        "out_bot": [round(pbot.dcenter[0] - 1.0, 3), round(pbot.dcenter[1], 3)],
    },
}
(HERE / "splitter_meta.json").write_text(json.dumps(meta, indent=2))
print("bbox:", round(c.xsize, 2), "x", round(c.ysize, 2), "um; ports:", meta["port_positions"])
