"""Parametric device script. Tunables are top-level name = value."""
import json
import gdsfactory as gf

w1 = 0.50
w2 = 0.54
l1 = 0.2431
l2 = 0.2431
n = 13

c = gf.components.dbr(w1=w1, w2=w2, l1=l1, l2=l2, n=n)
c.write_gds("device.gds", with_metadata=False)

# Measurement contract: emit lengths.json from the script's own tunables.
# A DBR's Bragg grating shape: period = l1 + l2, tooth widths w1 / w2.
with open("lengths.json", "w") as f:
    json.dump({"grating": {"period_um": l1 + l2, "w1_um": w1, "w2_um": w2}}, f)
