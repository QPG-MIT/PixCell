"""Parametric device script. Tunables are top-level name = value."""
import gdsfactory as gf

radius = 10.0
gap = 0.2
length_x = 4.0
length_y = 0.6

c = gf.components.ring_single(radius=radius, gap=gap, length_x=length_x, length_y=length_y)
c.write_gds("device.gds")
