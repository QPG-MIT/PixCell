"""Parametric device script. Tunables are top-level name = value."""
import json
from pathlib import Path

import gdsfactory as gf

delta_length = 18.0
length_y = 0.0
length_x = 0.1

c = gf.components.mzi(delta_length=delta_length, length_y=length_y, length_x=length_x)
c.write_gds("device.gds", with_metadata=False)


def _arm_length(component, names):
    total = 0.0
    wanted = set(names)
    for inst in component.insts:
        if inst.name in wanted:
            total += float(inst.cell.info["length"])
    return total


top_length = _arm_length(c, ("b1", "sytl", "b2", "sxt", "b3", "sytr", "b4"))
bottom_length = _arm_length(c, ("b5", "syl", "b6", "sxb", "b7", "sybr", "b8"))

Path("lengths.json").write_text(
    json.dumps(
        {
            "arms": {"top": top_length, "bottom": bottom_length},
            "delta_length_um": abs(bottom_length - top_length),
        },
        indent=2,
    )
)
