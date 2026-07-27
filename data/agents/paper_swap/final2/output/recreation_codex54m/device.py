from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

layer = (1, 0)
gds_name = "device_recreated.gds"

anchor_size = 0.01

body_x = 2.776
body_y = 2.652
body_width = 19.433
body_height = 3.753

top_stem_width = 1.218
top_stem_length = 1.322
top_base_width = 2.294
top_taper_length = 1.414

top_center_1 = 5.446
top_center_2 = 9.618
top_center_3 = 15.042
top_center_4 = 19.490

bottom_center_x = 12.486
bottom_base_width = 2.120
bottom_taper_length = 0.696
bottom_tip_width = 1.274
delta_length = 0.225


@gf.cell
def recreated_device() -> gf.Component:
    c = gf.Component("recreated_device")

    anchor_lo = c << gf.components.rectangle(size=(anchor_size, anchor_size), layer=layer)
    anchor_lo.move((0, 0))

    anchor_hi = c << gf.components.rectangle(size=(anchor_size, anchor_size), layer=layer)
    anchor_hi.move((25 - anchor_size, 10 - anchor_size))

    body = c << gf.components.rectangle(size=(body_width, body_height), layer=layer)
    body.move((body_x, body_y))

    top_taper = gf.components.taper(
        length=top_taper_length,
        width1=top_base_width,
        width2=top_stem_width,
        layer=layer,
        with_bbox=False,
    )
    top_stem = gf.components.rectangle(size=(top_stem_width, top_stem_length), layer=layer)

    for center_x in (top_center_1, top_center_2, top_center_3, top_center_4):
        taper_ref = c << top_taper
        taper_ref.rotate(90)
        taper_ref.move((center_x, body_y + body_height))

        stem_ref = c << top_stem
        stem_ref.move((center_x - top_stem_width / 2, body_y + body_height + top_taper_length))

    bottom_taper = c << gf.components.taper(
        length=bottom_taper_length,
        width1=bottom_base_width,
        width2=bottom_tip_width,
        layer=layer,
        with_bbox=False,
    )
    bottom_taper.rotate(-90)
    bottom_taper.move((bottom_center_x, body_y))

    bottom_tip = c << gf.components.rectangle(size=(bottom_tip_width, delta_length), layer=layer)
    bottom_tip.move((bottom_center_x - bottom_tip_width / 2, body_y - bottom_taper_length - delta_length))

    c.flatten()
    return c


if __name__ == "__main__":
    gf.clear_cache()
    component = recreated_device()

    reference_path = gf.Path()
    reference_path += gf.path.straight(length=bottom_taper_length)

    active_path = gf.Path()
    active_path += gf.path.straight(length=bottom_taper_length + delta_length)

    lengths_payload = {
        "arms": {
            "bottom_reference": round(reference_path.length(), 6),
            "bottom_finger": round(active_path.length(), 6),
        },
        "delta_length_um": round(active_path.length() - reference_path.length(), 6),
    }

    out_dir = Path(__file__).resolve().parent
    (out_dir / "lengths.json").write_text(json.dumps(lengths_payload, indent=2))
    component.write_gds(out_dir / gds_name, with_metadata=False)
