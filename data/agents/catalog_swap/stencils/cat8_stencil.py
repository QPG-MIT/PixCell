"""Parametric device script. Tunables are top-level name = value."""
import gdsfactory as gf

w1 = 0.475
w2 = 0.525
l1 = 0.159
l2 = 0.159
n = 20

c = gf.components.dbr(w1=w1, w2=w2, l1=l1, l2=l2, n=n)
c.write_gds("device.gds")
