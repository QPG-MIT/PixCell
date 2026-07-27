"""Parametric device script. Tunables are top-level name = value."""
import gdsfactory as gf

length = 100.0
spacing = 3.0
n_loops = 6

c = gf.components.spiral(length=length, spacing=spacing, n_loops=n_loops)
c.write_gds("device.gds")
