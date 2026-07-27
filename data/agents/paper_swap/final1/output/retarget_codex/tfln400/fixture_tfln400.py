from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

from device_tfln400 import (
    LAYER,
    footprint_length_um,
    input_center_y_um,
    lower_output_y_um,
    recreate_device,
    smoothstep,
    upper_output_y_um,
    wg_width_um,
)


input_stub_length_um = 3.0
fixture_fanout_length_um = 20.0
fixture_output_straight_length_um = 4.0
fixture_output_separation_um = 6.0
fixture_s_bend_points = 128


def make_s_bend_path(
    x0: float,
    y0: float,
    y1: float,
    bend_length: float,
    straight_length: float,
    npoints: int,
) -> gf.Path:
    points: list[tuple[float, float]] = []
    for i in range(npoints):
        t = i / (npoints - 1)
        points.append((x0 + bend_length * t, y0 + (y1 - y0) * smoothstep(t)))
    points.append((x0 + bend_length + straight_length, y1))
    return gf.Path(points)


@gf.cell
def make_fixture() -> gf.Component:
    c = gf.Component()
    c << recreate_device()

    c << gf.path.extrude(
        gf.Path([(-input_stub_length_um, input_center_y_um), (0.0, input_center_y_um)]),
        width=wg_width_um,
        layer=LAYER,
    )

    fixture_upper_y = fixture_output_separation_um / 2.0
    fixture_lower_y = -fixture_output_separation_um / 2.0

    upper_path = make_s_bend_path(
        footprint_length_um,
        upper_output_y_um,
        fixture_upper_y,
        fixture_fanout_length_um,
        fixture_output_straight_length_um,
        fixture_s_bend_points,
    )
    lower_path = make_s_bend_path(
        footprint_length_um,
        lower_output_y_um,
        fixture_lower_y,
        fixture_fanout_length_um,
        fixture_output_straight_length_um,
        fixture_s_bend_points,
    )
    c << gf.path.extrude(upper_path, width=wg_width_um, layer=LAYER)
    c << gf.path.extrude(lower_path, width=wg_width_um, layer=LAYER)
    return c


def write_meta(script_dir: Path) -> None:
    out_stub_start_x = footprint_length_um + fixture_fanout_length_um
    out_probe_x = out_stub_start_x + fixture_output_straight_length_um / 2.0
    payload = {
        "port_positions": {
            "in": [-input_stub_length_um / 2.0, input_center_y_um],
            "out_top": [out_probe_x, fixture_output_separation_um / 2.0],
            "out_bot": [out_probe_x, -fixture_output_separation_um / 2.0],
        }
    }
    (script_dir / "splitter_meta.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    fixture = make_fixture()
    flat_fixture = fixture.copy()
    flat_fixture.flatten()
    flat_fixture.write_gds(out_dir / "fixture_tfln400.gds", with_metadata=False)
    write_meta(out_dir)
