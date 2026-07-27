"""Parametric device script. Tunables are top-level name = value."""
import gdsfactory as gf

delta_length = 10.0
length_y = 2.0
length_x = 0.1

c = gf.components.mzi(delta_length=delta_length, length_y=length_y, length_x=length_x)
c.write_gds("device.gds")
