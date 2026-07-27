from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


LAYER = (1, 0)

wg_width = 0.5
mouth_width = 1.0
mmi_width = 2.5
mmi_length = 5.55
mouth_offset = 0.60

input_stub_length = 5.0
input_taper_length = 10.0
output_taper_length = 10.0
fanout_length = 15.0
output_stub_length = 8.0
output_y = 2.75


def _rect(c: gf.Component, x0: float, y0: float, sx: float, sy: float) -> None:
    ref = c << gf.components.rectangle(size=(sx, sy), layer=LAYER, centered=False)
    ref.move((x0, y0))


def _taper(
    c: gf.Component,
    x0: float,
    y: float,
    length: float,
    width1: float,
    width2: float,
) -> None:
    ref = c << gf.components.taper(
        length=length,
        width1=width1,
        width2=width2,
        layer=LAYER,
        with_bbox=False,
    )
    ref.move((x0, y))


def _s_bend(
    c: gf.Component,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    width: float = wg_width,
) -> None:
    dx = x1 - x0
    p0 = np.array((x0, y0))
    p1 = np.array((x0 + dx / 2, y0))
    p2 = np.array((x1 - dx / 2, y1))
    p3 = np.array((x1, y1))
    t = np.linspace(0.0, 1.0, 48)
    pts = (
        ((1 - t) ** 3)[:, None] * p0
        + (3 * (1 - t) ** 2 * t)[:, None] * p1
        + (3 * (1 - t) * t**2)[:, None] * p2
        + (t**3)[:, None] * p3
    )
    path = gf.Path([(float(x), float(y)) for x, y in pts])
    c << gf.path.extrude(path, layer=LAYER, width=width)


@gf.cell
def splitter_fixture() -> gf.Component:
    c = gf.Component()

    body_x0 = input_stub_length + input_taper_length
    body_x1 = body_x0 + mmi_length
    taper_x1 = body_x1 + output_taper_length
    fanout_x1 = taper_x1 + fanout_length
    out_x = fanout_x1 + output_stub_length

    _rect(c, 0.0, -wg_width / 2, input_stub_length, wg_width)
    _taper(c, input_stub_length, 0.0, input_taper_length, wg_width, mouth_width)
    _rect(c, body_x0, -mmi_width / 2, mmi_length, mmi_width)

    _taper(c, body_x1, mouth_offset, output_taper_length, mouth_width, wg_width)
    _taper(c, body_x1, -mouth_offset, output_taper_length, mouth_width, wg_width)

    _s_bend(c, taper_x1, mouth_offset, fanout_x1, output_y)
    _s_bend(c, taper_x1, -mouth_offset, fanout_x1, -output_y)
    _rect(c, fanout_x1, output_y - wg_width / 2, output_stub_length, wg_width)
    _rect(c, fanout_x1, -output_y - wg_width / 2, output_stub_length, wg_width)

    c.add_port("in", center=(0.0, 0.0), width=wg_width, orientation=180, layer=LAYER)
    c.add_port("out_top", center=(out_x, output_y), width=wg_width, orientation=0, layer=LAYER)
    c.add_port("out_bot", center=(out_x, -output_y), width=wg_width, orientation=0, layer=LAYER)
    return c


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    gds_path = out_dir / "splitter_soi220.gds"
    meta_path = out_dir / "splitter_meta.json"

    c = splitter_fixture()
    c.write_gds(gds_path, with_metadata=False)

    body_x0 = input_stub_length + input_taper_length
    out_x = body_x0 + mmi_length + output_taper_length + fanout_length + output_stub_length
    meta = {
        "port_positions": {
            "in": [0.0, 0.0],
            "out_top": [out_x, output_y],
            "out_bot": [out_x, -output_y],
        }
    }
    meta_path.write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
