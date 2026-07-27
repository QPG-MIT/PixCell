from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Footprint and access guides.
footprint_length_um = 8.0
footprint_width_um = 8.0
port_width_um = 0.5044
horizontal_extra_length_um = 0.0

# Function-defining sampled profile of the expanded crossing body.
# Widths are full material widths of one variable-width waveguide axis.
knot_snap_um = 0.002
center_width_um = 7.996
knot_025_width_um = 7.996
knot_050_width_um = 5.334
knot_075_width_um = 4.384
knot_100_width_um = 2.486
knot_125_width_um = 1.998
knot_150_width_um = 1.898
knot_175_width_um = 1.778
knot_200_width_um = 1.6280
knot_225_width_um = 1.448
knot_250_width_um = 1.198
knot_275_width_um = 0.858
knot_300_width_um = 0.704
knot_325_width_um = 0.654
knot_350_width_um = 0.604
knot_375_width_um = 0.554
edge_width_um = port_width_um


def _profile_knots() -> list[tuple[float, float]]:
    return [
        (-4.0, edge_width_um),
        (-3.75, knot_375_width_um),
        (-3.5, knot_350_width_um),
        (-3.25, knot_325_width_um),
        (-3.0, knot_300_width_um),
        (-2.75, knot_275_width_um),
        (-2.5, knot_250_width_um),
        (-2.25, knot_225_width_um),
        (-2.0, knot_200_width_um),
        (-1.75, knot_175_width_um),
        (-1.5, knot_150_width_um),
        (-1.25, knot_125_width_um),
        (-1.0, knot_100_width_um),
        (-0.75, knot_075_width_um),
        (-0.5, knot_050_width_um),
        (-0.25, knot_025_width_um),
        (0.0, center_width_um),
        (0.25, knot_025_width_um),
        (0.5, knot_050_width_um),
        (0.75, knot_075_width_um),
        (1.0, knot_100_width_um),
        (1.25, knot_125_width_um),
        (1.5, knot_150_width_um),
        (1.75, knot_175_width_um),
        (2.0, knot_200_width_um),
        (2.25, knot_225_width_um),
        (2.5, knot_250_width_um),
        (2.75, knot_275_width_um),
        (3.0, knot_300_width_um),
        (3.25, knot_325_width_um),
        (3.5, knot_350_width_um),
        (3.75, knot_375_width_um),
        (4.0, edge_width_um),
    ]


def _axis_component(name: str, vertical: bool = False) -> gf.Component:
    c = gf.Component(name)
    extension_each_side = horizontal_extra_length_um / 2 if not vertical else 0.0
    knots = _profile_knots()
    knots = [(x - extension_each_side if i == 0 else x, w) for i, (x, w) in enumerate(knots)]
    knots[-1] = (knots[-1][0] + extension_each_side, knots[-1][1])

    for (x0, w0), (x1, w1) in zip(knots[:-1], knots[1:]):
        length = x1 - x0
        taper = gf.components.taper(
            length=length,
            width1=w0,
            width2=w1,
            layer=LAYER,
            with_bbox=False,
        )
        ref = c << taper
        if vertical:
            ref.drotate(90)
            ref.dmove((0, x0))
        else:
            ref.dmove((x0, 0))
    return c


@gf.cell
def recreated_crossing() -> gf.Component:
    horizontal = _axis_component("horizontal_axis")
    vertical = _axis_component("vertical_axis", vertical=True)
    merged = gf.boolean(horizontal, vertical, operation="or", layer=LAYER)

    c = gf.Component()
    c << merged
    return c


def _write_lengths(out_dir: Path) -> None:
    lengths = {
        "arms": {
            "horizontal": footprint_length_um + horizontal_extra_length_um,
            "vertical": footprint_width_um,
        },
        "delta_length_um": horizontal_extra_length_um,
    }
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    component = recreated_crossing().copy()
    component.flatten()
    component.write_gds(out_dir / "device.gds")
    _write_lengths(out_dir)
