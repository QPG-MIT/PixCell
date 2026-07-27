from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

layer = (1, 0)
footprint_um = 4.7
stem_width_um = 0.228
stem_length_um = 0.52
lobe_major_um = 1.02
lobe_minor_um = 0.455
lobe_offset_um = 0.83
delta_length = 0.0


def clover_device() -> gf.Component:
    c = gf.Component("clover_device")

    refs = []
    for sign in (-1, 1):
        east_west = c << gf.components.ellipse(
            radii=(lobe_major_um, lobe_minor_um),
            layer=layer,
            angle_resolution=2.0,
        )
        east_west.move((sign * lobe_offset_um, 0))
        refs.append(east_west)

        north_south = c << gf.components.ellipse(
            radii=(lobe_minor_um, lobe_major_um),
            layer=layer,
            angle_resolution=2.0,
        )
        north_south.move((0, sign * lobe_offset_um))
        refs.append(north_south)

    east = c << gf.components.rectangle(size=(stem_length_um, stem_width_um), layer=layer)
    east.move((lobe_offset_um + lobe_major_um - 1e-3, -stem_width_um / 2))
    refs.append(east)

    west = c << gf.components.rectangle(size=(stem_length_um, stem_width_um), layer=layer)
    west.move((-(lobe_offset_um + lobe_major_um + stem_length_um) + 1e-3, -stem_width_um / 2))
    refs.append(west)

    north_length_um = stem_length_um + delta_length / 2
    south_length_um = stem_length_um + delta_length / 2

    north = c << gf.components.rectangle(size=(stem_width_um, north_length_um), layer=layer)
    north.move((-stem_width_um / 2, lobe_offset_um + lobe_major_um - 1e-3))
    refs.append(north)

    south = c << gf.components.rectangle(size=(stem_width_um, south_length_um), layer=layer)
    south.move((-stem_width_um / 2, -(lobe_offset_um + lobe_major_um + south_length_um) + 1e-3))
    refs.append(south)

    c.flatten()
    return c


def write_lengths(script_dir: Path) -> None:
    horizontal_arm_um = 2 * (stem_length_um + lobe_offset_um + lobe_major_um)
    vertical_arm_um = horizontal_arm_um + delta_length
    payload = {
        "arms": {
            "horizontal_um": horizontal_arm_um,
            "vertical_um": vertical_arm_um,
        },
        "delta_length_um": abs(vertical_arm_um - horizontal_arm_um),
    }
    (script_dir / "lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    component = clover_device()
    component.write_gds(script_dir / "device.gds")
    write_lengths(script_dir)
