import json
from pathlib import Path

import gdsfactory as gf


layer = (1, 0)

footprint_length_um = 25.0
footprint_width_um = 10.0

body_height_um = 5.12
body_bottom_y_um = 1.36
body_corner_radius_um = 0.18

stem_tip_width_um = 1.58
stem_base_width_um = 3.10
stem_straight_length_um = 1.80
stem_taper_length_um = 2.10
stem_centers_um = (3.46, 8.78, 15.77, 21.47)
stem_tip_y_um = 10.0

nub_length_um = 1.36
nub_tip_width_um = 1.55
nub_base_width_um = 3.10

probe_width_um = 0.40
delta_length = 0.00
probe_reference_length_um = stem_straight_length_um + stem_taper_length_um
def build_component() -> gf.Component:
    tmp = gf.Component("device_tmp")

    body_width_um = 19.40
    body_x_um = (footprint_length_um - body_width_um) / 2
    body = gf.components.rectangle(size=(body_width_um, body_height_um), layer=layer)
    body_ref = tmp << body
    body_ref.move((body_x_um, body_bottom_y_um))

    # Upper fingers: straight tip plus taper into the body.
    stem_tip_bottom_y = stem_tip_y_um - stem_straight_length_um
    stem_base_bottom_y = stem_tip_bottom_y - stem_taper_length_um
    for idx, x_center in enumerate(stem_centers_um):
        straight_length = stem_straight_length_um + (delta_length if idx == len(stem_centers_um) - 1 else 0.0)
        straight = gf.components.straight(length=straight_length, width=stem_tip_width_um)
        straight_ref = tmp << straight
        straight_ref.rotate(90)
        straight_ref.move((x_center, stem_tip_bottom_y if idx == len(stem_centers_um) - 1 else stem_tip_y_um - straight_length))

        taper = gf.components.taper(
            length=stem_taper_length_um,
            width1=stem_base_width_um,
            width2=stem_tip_width_um,
            layer=layer,
        )
        taper_ref = tmp << taper
        taper_ref.rotate(90)
        taper_ref.move((x_center, stem_base_bottom_y))

    # Lower taper protrusion.
    nub = gf.components.taper(length=nub_length_um, width1=nub_base_width_um, width2=nub_tip_width_um, layer=layer)
    nub_ref = tmp << nub
    nub_ref.rotate(90)
    nub_ref.move((footprint_length_um / 2, 0.0))

    # Tiny corner markers keep the absolute bbox at the full footprint without
    # materially affecting the raster silhouette.
    corner_marker_um = 0.01
    corner = gf.components.rectangle(size=(corner_marker_um, corner_marker_um), layer=layer)
    left_corner = tmp << corner
    left_corner.move((0.0, footprint_width_um - corner_marker_um))
    right_corner = tmp << corner
    right_corner.move((footprint_length_um - corner_marker_um, footprint_width_um - corner_marker_um))

    # Union everything into a single outline so area is not double-counted.
    merged = gf.boolean(tmp, tmp, operation="or", layer=layer, layer1=layer, layer2=layer)
    merged.name = "device"
    return merged


def write_lengths_json(out_dir: Path) -> None:
    left_stem_length_um = stem_straight_length_um + stem_taper_length_um
    right_stem_length_um = stem_straight_length_um + stem_taper_length_um + delta_length
    lengths = {
        "arms": {
            "left_stem": left_stem_length_um,
            "right_stem": right_stem_length_um,
        },
        "delta_length_um": delta_length,
    }
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))


def main() -> None:
    out_dir = Path(__file__).resolve().parent
    component = build_component()
    component.write_gds(out_dir / "device.gds")
    write_lengths_json(out_dir)


if __name__ == "__main__":
    main()
