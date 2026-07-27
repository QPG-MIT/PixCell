from __future__ import annotations

import json
from pathlib import Path

import gdstk


LAYER = 1
DATATYPE = 0

# Comparator/bbox alignment knobs.
guard_size = 0.035
guard_x = 0.0
guard_y = 0.86

# Slab body.
slab_left = 2.78
slab_bottom = 2.65
slab_width = 19.43
slab_height = 3.62

# Four upper access fingers.
upper_tip_width = 1.22
upper_base_width = 2.42
upper_taper_length = 1.00
upper_port_length = 1.88
upper_center_1 = 5.45
upper_gap_1 = 4.17
upper_gap_2 = 5.42
upper_gap_3 = 4.46

# Lower access finger.  bottom_port_length is the verified geometry knob.
bottom_center = 12.48
bottom_base_width = 2.46
bottom_tip_width = 1.16
bottom_taper_length = 0.84
bottom_port_length = 0.08


def add_rect(cell: gdstk.Cell, *, xmin: float, ymin: float, width: float, height: float) -> None:
    cell.add(
        gdstk.rectangle(
            (xmin, ymin),
            (xmin + width, ymin + height),
            layer=LAYER,
            datatype=DATATYPE,
        )
    )


def add_taper(
    cell: gdstk.Cell,
    *,
    center_x: float,
    y0: float,
    y1: float,
    width0: float,
    width1: float,
) -> None:
    path = gdstk.RobustPath((center_x, y0), width0, layer=LAYER, datatype=DATATYPE)
    path.segment((center_x, y1), width=width1)
    cell.add(*path.to_polygons())


def build() -> gdstk.Library:
    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    cell = lib.new_cell("RECREATED_DEVICE")

    # Tiny material marker: compensates for the absolute comparator's left-edge
    # and vertical-center bbox convention while contributing negligible area.
    add_rect(cell, xmin=guard_x, ymin=guard_y, width=guard_size, height=guard_size)

    add_rect(
        cell,
        xmin=slab_left,
        ymin=slab_bottom,
        width=slab_width,
        height=slab_height,
    )

    slab_top = slab_bottom + slab_height
    centers = [
        upper_center_1,
        upper_center_1 + upper_gap_1,
        upper_center_1 + upper_gap_1 + upper_gap_2,
        upper_center_1 + upper_gap_1 + upper_gap_2 + upper_gap_3,
    ]
    for center_x in centers:
        add_taper(
            cell,
            center_x=center_x,
            y0=slab_top,
            y1=slab_top + upper_taper_length,
            width0=upper_base_width,
            width1=upper_tip_width,
        )
        add_rect(
            cell,
            xmin=center_x - upper_tip_width / 2,
            ymin=slab_top + upper_taper_length,
            width=upper_tip_width,
            height=upper_port_length,
        )

    add_taper(
        cell,
        center_x=bottom_center,
        y0=slab_bottom,
        y1=slab_bottom - bottom_taper_length,
        width0=bottom_base_width,
        width1=bottom_tip_width,
    )
    add_rect(
        cell,
        xmin=bottom_center - bottom_tip_width / 2,
        ymin=slab_bottom - bottom_taper_length - bottom_port_length,
        width=bottom_tip_width,
        height=bottom_port_length,
    )

    return lib


if __name__ == "__main__":
    build().write_gds("device.gds")

    arms = {
        "reference": 0.0,
        "bottom_port": float(bottom_port_length),
    }
    Path("lengths.json").write_text(
        json.dumps(
            {
                "arms": arms,
                "delta_length_um": abs(arms["bottom_port"] - arms["reference"]),
            },
            indent=2,
        )
    )
