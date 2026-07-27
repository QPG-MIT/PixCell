"""Parametric device script. Tunables are top-level name = value."""
import json
import gdsfactory as gf

delta_length = 18.0
length_y = 0.0
length_x = 0.1

c = gf.components.mzi(delta_length=delta_length, length_y=length_y, length_x=length_x)
c.write_gds("device.gds", with_metadata=False)

# Measurement contract: derive the two MZI arm lengths from the component's OWN
# straight instances (never hand-entered) and write lengths.json next to the GDS.
# gf.components.mzi realizes the path imbalance by lengthening one arm's vertical
# straights: bottom arm = {sxb, syl, sybr}, top arm = {sxt, sytl, sytr}. Bends are
# equal on both arms and cancel in the difference, so the straight-sum difference
# is the true optical-path delta.
_straights = {}
for _name, _inst in c.get_netlist()["instances"].items():
    if _name.startswith("s"):
        _straights[_name] = float(_inst.get("settings", {}).get("length", 0.0))

_bottom = sum(_straights.get(k, 0.0) for k in ("sxb", "syl", "sybr"))
_top = sum(_straights.get(k, 0.0) for k in ("sxt", "sytl", "sytr"))
_arms = {"bottom": _bottom, "top": _top}
_delta = abs(_bottom - _top)

with open("lengths.json", "w") as _f:
    json.dump({"arms": _arms, "delta_length_um": _delta}, _f, indent=2)
