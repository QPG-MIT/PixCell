"""Parametric device script. Tunables are top-level name = value."""
import gdsfactory as gf
import functools
import math
import json

# platform constant (rule-based per stack: waveguide width = single_mode_width_um)
width = 1.2

# tunables
radius = 5.0
gap = 0.5
length_x = 14.0
length_y = 8.9

xs = functools.partial(gf.cross_section.strip, width=width)
c = gf.components.ring_single(
    radius=radius, gap=gap, length_x=length_x, length_y=length_y, cross_section=xs
)
c.write_gds("device.gds", with_metadata=False)

# measurement contract: ring round-trip optical path, from its own geometry
# (racetrack: two pi-radius bends + two length_x + two length_y straights).
round_trip_um = 2.0 * math.pi * radius + 2.0 * length_x + 2.0 * length_y
json.dump({"ring": {"round_trip_um": round_trip_um}}, open("lengths.json", "w"), indent=1)
