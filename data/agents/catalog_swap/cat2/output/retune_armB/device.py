"""Parametric device script. Tunables are top-level name = value."""
import json
from pathlib import Path

import gdsfactory as gf

radius = 5.0
length_x = 14.0
gap = 0.5
length_y = 10.3


def _ring_round_trip_um() -> float:
    bend = gf.components.bend_euler(radius=radius)
    bend_length = float(bend.info["length"])
    return 4 * bend_length + 2 * length_x + 2 * length_y


c = gf.components.ring_single(radius=radius, gap=gap, length_x=length_x, length_y=length_y)
c = c.copy()
c.flatten()
c.write_gds("device.gds", with_metadata=False)
(Path(__file__).with_name("lengths.json")).write_text(
    json.dumps({"ring": {"round_trip_um": _ring_round_trip_um()}}, indent=2)
)
