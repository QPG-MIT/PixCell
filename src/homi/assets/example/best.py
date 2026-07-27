from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


layer = (1, 0)

footprint_length = 24.3
body_width = 5.0

body_x0 = 3.0267
body_length = 12.3085

wg_width = 0.306

input_taper_length = 3.0267
input_tip_width = 0.306
input_body_width = 0.626

output_taper_length = 4.3818
output_straight_length = 4.5830
output_body_width = 0.626

output_y_top_1 = 0.6848
output_pitch_top_mid = 1.0720
output_pitch_mid_mid = 1.3990
output_pitch_bottom_mid = 1.1520


def _top_to_gds_y(y_top: float) -> float:
    return body_width - y_top


def _add_centered_x_section(
    component: gf.Component,
    section: gf.Component,
    x0: float,
    y_center: float,
) -> None:
    ref = component.add_ref(section)
    ref.dxmin = x0
    ref.dcenter = (ref.dcenter[0], y_center)


@gf.cell
def recreate_device() -> gf.Component:
    c = gf.Component()

    body = gf.components.rectangle(
        size=(body_length, body_width),
        layer=layer,
        centered=False,
    )
    body_ref = c.add_ref(body)
    body_ref.dxmin = body_x0
    body_ref.dymin = 0

    input_taper = gf.components.taper(
        length=input_taper_length,
        width1=input_tip_width,
        width2=input_body_width,
        layer=layer,
    )
    _add_centered_x_section(c, input_taper, 0.0, body_width / 2)

    output_y_top_2 = output_y_top_1 + output_pitch_top_mid
    output_y_top_3 = output_y_top_2 + output_pitch_mid_mid
    output_y_top_4 = output_y_top_3 + output_pitch_bottom_mid
    output_y_centers = [
        _top_to_gds_y(output_y_top_1),
        _top_to_gds_y(output_y_top_2),
        _top_to_gds_y(output_y_top_3),
        _top_to_gds_y(output_y_top_4),
    ]

    output_taper = gf.components.taper(
        length=output_taper_length,
        width1=output_body_width,
        width2=wg_width,
        layer=layer,
    )
    output_straight = gf.components.rectangle(
        size=(output_straight_length, wg_width),
        layer=layer,
        centered=False,
    )

    body_x1 = body_x0 + body_length
    straight_x0 = body_x1 + output_taper_length
    for y_center in output_y_centers:
        _add_centered_x_section(c, output_taper, body_x1, y_center)
        _add_centered_x_section(c, output_straight, straight_x0, y_center)

    c.flatten()
    return c


def write_lengths(script_path: Path) -> None:
    payload = {
        "arms": {
            "reference": 0.0,
            "multimode_body": float(body_length),
        },
        "delta_length_um": float(body_length),
    }
    script_path.with_name("lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    component = recreate_device()
    component.write_gds(here / "device.gds", with_metadata=False)
    write_lengths(Path(__file__).resolve())
