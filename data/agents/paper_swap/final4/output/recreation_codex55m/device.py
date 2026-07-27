from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf


layer = (1, 0)

# Footprint and port geometry, um.
length_um = 18.0
height_um = 3.0
wg_width = 0.652
port_pitch = 2.342
central_gap = 0.300

# Directional-coupler function knobs, um.
coupling_length = 2.2
transition_length = 6.8
profile_exponent = 0.75

# Single-guide trim used by the HOMI knob-response verifier.
delta_length = 0.0

num_points = 257
gds_out = "device.gds"


def smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def raised_profile(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return smoothstep(t) ** profile_exponent


def separation_at_x(x: float) -> float:
    sep_outer = port_pitch
    sep_inner = wg_width + central_gap
    half_coupler = coupling_length / 2.0
    center = length_um / 2.0
    d = abs(x - center)
    if d <= half_coupler:
        return sep_inner
    transition = max(0.001, (length_um - coupling_length) / 2.0)
    t = (d - half_coupler) / transition
    return sep_inner + (sep_outer - sep_inner) * raised_profile(t)


def path_points(sign: float, extra_length: float = 0.0) -> list[tuple[float, float]]:
    pts = []
    denom = max(1, num_points - 1)
    for i in range(num_points):
        x = length_um * i / denom
        y = height_um / 2.0 + sign * separation_at_x(x) / 2.0
        pts.append((x, y))
    if extra_length > 0:
        pts.append((length_um + extra_length, pts[-1][1]))
    return pts


def polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(x1 - x0, y1 - y0)
        for (x0, y0), (x1, y1) in zip(points, points[1:])
    )


@gf.cell
def recreate() -> gf.Component:
    c = gf.Component()
    top_pts = path_points(+1.0, delta_length)
    bot_pts = path_points(-1.0, 0.0)

    top = gf.Path(top_pts).extrude(width=wg_width, layer=layer)
    bot = gf.Path(bot_pts).extrude(width=wg_width, layer=layer)
    c << top
    c << bot

    lengths = {
        "arms": {
            "top": polyline_length(top_pts),
            "bottom": polyline_length(bot_pts),
        },
        "delta_length_um": polyline_length(top_pts) - polyline_length(bot_pts),
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(lengths, indent=2))
    return c


if __name__ == "__main__":
    component = recreate()
    component.write_gds(Path(__file__).with_name(gds_out), with_metadata=False)
