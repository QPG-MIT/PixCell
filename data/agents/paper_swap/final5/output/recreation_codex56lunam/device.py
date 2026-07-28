import math
import json
from pathlib import Path

import gdsfactory as gf

wg_width = 0.028
center_width = 0.014
bend_radius = 1.55
taper_length = 1.15
coupling_start = 4.05
delta_length = 9.50
coupling_end = coupling_start + delta_length
tooth_pitch = 0.18
tooth_width = 0.075
tooth_depth = 0.030
top_coupling_y = 0.155
bottom_coupling_y = 0.220
center_y = 0.185
top_port_y = 0.025
bottom_port_y = 0.355


def _polyline(points, width=wg_width):
    return gf.path.extrude(gf.Path(points), width=width, layer=(1, 0), simplify=0.001)


def _arc_points(cx, cy, radius, a0, a1, n=24):
    return [(cx + radius * math.cos(a0 + (a1 - a0) * i / n),
             cy + radius * math.sin(a0 + (a1 - a0) * i / n)) for i in range(n + 1)]


def _add_taper(c, x, y, angle, width=wg_width):
    t = gf.components.taper(length=taper_length, width1=0.002, width2=width, layer=(1, 0))
    ref = c << t
    ref.center = (x + math.cos(angle) * taper_length / 2, y + math.sin(angle) * taper_length / 2)
    ref.rotate(angle)


def _add_periodic_section(c, x0, x1, y, width=wg_width):
    x = x0
    while x + tooth_width <= x1 + 1e-9:
        r = gf.components.rectangle(size=(tooth_width, width), layer=(1, 0))
        ref = c << r
        ref.center = (x + tooth_width / 2, y)
        x += tooth_pitch


@gf.cell
def device():
    c = gf.Component("recreated_periodic_dual_route")
    left_top = [(0.0, top_port_y), (0.35, top_port_y)]
    left_top += [(0.35 + 3.70 * math.cos(t), top_coupling_y + 0.143 * math.sin(t))
                 for t in [(-math.pi / 2) + (math.pi / 2) * i / 24 for i in range(1, 25)]]
    left_top += [(coupling_start, top_coupling_y)]
    c.add_ref(_polyline(left_top))
    right_top = [(coupling_end, top_coupling_y)]
    right_top += [(coupling_end + 2.17 * math.sin(math.pi * i / 48),
                   top_coupling_y - 0.143 * (1 - math.cos(math.pi * i / 48)))
                  for i in range(1, 25)]
    right_top += [(15.72, top_port_y)]
    c.add_ref(_polyline(right_top))
    top_bar = gf.components.rectangle(size=(14.44, wg_width), layer=(1, 0))
    top_bar_ref = c << top_bar
    top_bar_ref.center = (8.50, top_port_y)
    _add_periodic_section(c, coupling_start, coupling_end, top_coupling_y)

    left_bottom = [(2.18, bottom_port_y)]
    left_bottom += [(2.18 + 1.87 * math.sin(math.pi * i / 48),
                     bottom_coupling_y + 0.135 * math.cos(math.pi * i / 48))
                    for i in range(1, 25)]
    left_bottom += [(coupling_start, bottom_coupling_y)]
    c.add_ref(_polyline(left_bottom))
    right_bottom = [(coupling_end, bottom_coupling_y)]
    right_bottom += [(coupling_end + 4.40 * math.sin(math.pi * i / 48),
                      bottom_coupling_y + 0.135 * (1 - math.cos(math.pi * i / 48)))
                     for i in range(1, 25)]
    right_bottom += [(17.95, bottom_port_y)]
    c.add_ref(_polyline(right_bottom))
    bottom_bar = gf.components.rectangle(size=(15.77, wg_width), layer=(1, 0))
    bottom_bar_ref = c << bottom_bar
    bottom_bar_ref.center = (10.065, bottom_port_y)
    # The reference image has a narrow down-going exit after the broad lower bar.
    c.add_ref(_polyline([(17.95, bottom_port_y), (18.20, 0.688)], width=0.006))
    _add_periodic_section(c, coupling_start, coupling_end, bottom_coupling_y)

    bus = gf.components.rectangle(size=(16.55, center_width), layer=(1, 0))
    bus_ref = c << bus
    bus_ref.center = (9.12, center_y)
    c.flatten()
    return c


if __name__ == "__main__":
    out = Path(__file__).with_suffix(".gds")
    device().write_gds(out)
    json.dump({"arms": {"top": coupling_end + 4.0, "bottom": coupling_end + 4.0 + delta_length},
               "delta_length_um": delta_length}, open(out.with_name("lengths.json"), "w"))
