"""Parametric device script. Tunables are top-level name = value."""
import gdsfactory as gf

width = 0.5
r1 = 3.0
r2 = 1.1
w = 1.2

c = gf.components.crossing45() if False else gf.components.crossing()
c.write_gds("device.gds")
# NOTE: gf.components.crossing exposes no numeric knobs at this API level —
# that absence IS data for the representation ladder.
