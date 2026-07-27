"""Parametric device script. Tunables are top-level name = value."""
import gdsfactory as gf

gap = 0.236
length = 20.0
dy = 4.0
dx = 10.0

c = gf.components.coupler(gap=gap, length=length, dy=dy, dx=dx)
c.write_gds("device.gds")
