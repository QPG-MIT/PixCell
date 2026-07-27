"""Parametric device script. Tunables are top-level name = value."""
import gdsfactory as gf
import json

length = 108.089
spacing = 1.0
n_loops = 12

c = gf.components.spiral(length=length, spacing=spacing, n_loops=n_loops)
c.write_gds("device.gds", with_metadata=False)

# Measurement contract: report the centerline path length from the built
# component (group_delay_ps -> {"path": {"total_um": L}}), never hand-entered.
json.dump({"path": {"total_um": float(c.info["length"])}}, open("lengths.json", "w"), indent=2)
