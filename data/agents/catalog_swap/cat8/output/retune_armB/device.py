"""Parametric device script. Tunables are top-level name = value."""
import json

import gdsfactory as gf

w1 = 0.5
w2 = 0.55
l1 = 0.24262565509276998
l2 = 0.24262565509276998
n = 13

c = gf.components.dbr(w1=w1, w2=w2, l1=l1, l2=l2, n=n)
flat = c.copy()
flat.flatten()
flat.write_gds("device.gds", with_metadata=False)

with open("lengths.json", "w") as f:
    json.dump(
        {
            "grating": {
                "period_um": l1 + l2,
                "w1_um": w1,
                "w2_um": w2,
            }
        },
        f,
        indent=2,
    )
