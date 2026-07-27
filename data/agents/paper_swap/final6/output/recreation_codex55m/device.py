from __future__ import annotations

import json
from pathlib import Path

import gdstk


# Top-level tunables.
layer = 1
datatype = 0
footprint_um = 4.7
guide_width_um = 0.22
flare_width_um = 0.92
flare_length_um = 1.65
port_stub_um = 0.48
center_overlap_um = 0.62
delta_length = 0.0


def rectangle(cell: gdstk.Cell, name: str, xmin: float, ymin: float, xmax: float, ymax: float) -> None:
    poly = gdstk.rectangle((xmin, ymin), (xmax, ymax), layer=layer, datatype=datatype)
    poly.properties = [("name", name)]
    cell.add(poly)


def lens(cell: gdstk.Cell, name: str, cx: float, cy: float, rx: float, ry: float) -> None:
    poly = gdstk.ellipse(
        (cx, cy),
        radius=(rx, ry),
        tolerance=0.0007,
        layer=layer,
        datatype=datatype,
    )
    poly.properties = [("name", name)]
    cell.add(poly)


def build() -> gdstk.Library:
    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    cell = lib.new_cell("DEVICE")

    half = footprint_um / 2
    half_w = guide_width_um / 2
    half_flare = flare_width_um / 2
    lobe_center = (flare_length_um - center_overlap_um) / 2
    lobe_radius = (flare_length_um + center_overlap_um) / 2

    rectangle(cell, "west_port", -half, -half_w, -half + port_stub_um, half_w)
    rectangle(
        cell,
        "east_port",
        half - port_stub_um,
        -half_w,
        half + delta_length,
        half_w,
    )
    rectangle(cell, "south_port", -half_w, -half, half_w, -half + port_stub_um)
    rectangle(cell, "north_port", -half_w, half - port_stub_um, half_w, half)

    lens(cell, "west_flare", -lobe_center, 0, lobe_radius, half_flare)
    lens(cell, "east_flare", lobe_center, 0, lobe_radius, half_flare)
    lens(cell, "south_flare", 0, -lobe_center, half_flare, lobe_radius)
    lens(cell, "north_flare", 0, lobe_center, half_flare, lobe_radius)
    return lib


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    library = build()
    library.write_gds(here / "device.gds")

    base_len = port_stub_um + flare_length_um + center_overlap_um
    east_len = base_len + delta_length
    (here / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {"west": base_len, "east": east_len},
                "delta_length_um": abs(east_len - base_len),
            },
            indent=2,
        )
    )
