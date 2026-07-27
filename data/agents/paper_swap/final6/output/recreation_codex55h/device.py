from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Top-level tunables, um.
footprint_um = 4.7
wg_width = 0.23
stem_length = 0.55
taper_length = 0.87
lobe_width = 0.92
center_width = 0.62
transfer_length = 0.0

output_gds = "device.gds"


def _xs(width: float) -> gf.CrossSection:
    return gf.cross_section.cross_section(width=width, layer=LAYER)


@gf.cell
def _segment(length: float, width1: float, width2: float) -> gf.Component:
    path = gf.path.straight(length=length, npoints=48)
    transition = gf.path.transition(
        _xs(width1),
        _xs(width2),
        width_type="sine",
        offset_type="linear",
    )
    return gf.path.extrude_transition(path, transition)


def _add_x_segment(
    component: gf.Component,
    x0: float,
    x1: float,
    y: float,
    width1: float,
    width2: float,
) -> None:
    ref = component << _segment(length=x1 - x0, width1=width1, width2=width2)
    ref.move((x0, y))


def _add_y_segment(
    component: gf.Component,
    y0: float,
    y1: float,
    x: float,
    width1: float,
    width2: float,
) -> None:
    ref = component << _segment(length=y1 - y0, width1=width1, width2=width2)
    ref.rotate(90)
    ref.move((x, y0))


@gf.cell
def device() -> gf.Component:
    center = footprint_um / 2
    peak0 = stem_length + taper_length
    peak1 = footprint_um - stem_length - taper_length

    primitives = gf.Component()

    _add_x_segment(primitives, 0, stem_length, center, wg_width, wg_width)
    _add_x_segment(primitives, stem_length, peak0, center, wg_width, lobe_width)
    _add_x_segment(primitives, peak0, center, center, lobe_width, center_width)
    _add_x_segment(primitives, center, peak1, center, center_width, lobe_width)
    _add_x_segment(primitives, peak1, footprint_um - stem_length, center, lobe_width, wg_width)
    _add_x_segment(primitives, footprint_um - stem_length, footprint_um, center, wg_width, wg_width)

    _add_y_segment(primitives, 0, stem_length, center, wg_width, wg_width)
    _add_y_segment(primitives, stem_length, peak0, center, wg_width, lobe_width)
    _add_y_segment(primitives, peak0, center, center, lobe_width, center_width)
    _add_y_segment(primitives, center, peak1, center, center_width, lobe_width)
    _add_y_segment(primitives, peak1, footprint_um - stem_length, center, lobe_width, wg_width)
    _add_y_segment(primitives, footprint_um - stem_length, footprint_um, center, wg_width, wg_width)

    if transfer_length > 1e-9:
        _add_x_segment(
            primitives,
            footprint_um,
            footprint_um + transfer_length,
            center,
            wg_width,
            wg_width,
        )

    empty = gf.Component()
    return gf.boolean(A=primitives, B=empty, operation="or", layer=LAYER)


def write_lengths() -> None:
    horizontal_path = gf.path.straight(length=footprint_um + transfer_length)
    vertical_path = gf.path.straight(length=footprint_um)
    horizontal = float(horizontal_path.length())
    vertical = float(vertical_path.length())
    payload = {
        "arms": {"horizontal": horizontal, "vertical": vertical},
        "delta_length_um": abs(horizontal - vertical),
    }
    Path("lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    c = device()
    c.write_gds(output_gds, with_metadata=False)
    write_lengths()
