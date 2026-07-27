"""Parametric device script. Tunables are top-level name = value."""
import json
import gdsfactory as gf

gap = 0.5
length = 174.61
dy = 4.0
dx = 10.0

c = gf.components.coupler(gap=gap, length=length, dy=dy, dx=dx)
c = c.copy()
c.flatten()
c.write_gds("device.gds", with_metadata=False)

# Measurement-contract sidecar (not a device element): the spec evaluator's
# coupling_ratio metric reads the coupler shape {length_um, gap_um} from
# lengths.json; width defaults to the stack single_mode_width_um. Values are
# the coupling-region straight length and edge-to-edge gap tunables above.
with open("lengths.json", "w") as f:
    json.dump({"coupler": {"length_um": length, "gap_um": gap}}, f, indent=2)
