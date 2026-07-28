import json
from pathlib import Path

import gdsfactory as gf


# Image-calibrated, function-defining dimensions (um).
body_length = 19.5
body_width = 3.5
body_x = 2.75
body_y = 3.90
guide_width = 1.25
finger_pitch = 4.45
finger_x0 = 5.45
finger_straight_length = 0.85
taper_length = 2.15
taper_base_width = 2.40
lower_taper_length = 1.45
lower_taper_tip_width = 0.85
delta_length = 0.85
layer = (1, 0)


def _place_bbox(ref, xmin, ymin, xmax, ymax):
    """Place a reference by its transformed bounding box."""
    ref.move((xmin - ref.xmin, ymin - ref.ymin))
    if abs((ref.xmax - ref.xmin) - (xmax - xmin)) > 0.02:
        raise ValueError("primitive placement width mismatch")


@gf.cell
def device():
    c = gf.Component("recreation")

    body = c << gf.components.rectangle(size=(body_length, body_width), layer=layer)
    body.move((body_x, body_y))

    # Four narrow stems and their widening transitions on the upper edge.
    for i in range(4):
        cx = finger_x0 + i * finger_pitch
        stem_length = delta_length if i == 0 else finger_straight_length
        stem = c << gf.components.rectangle(
            size=(guide_width, stem_length), layer=layer
        )
        stem_y = body_y + body_width + taper_length if i == 0 else body_y + body_width
        stem.move((cx - guide_width / 2, stem_y))

        taper = c << gf.components.taper(
            length=taper_length,
            width1=taper_base_width,
            width2=guide_width,
            layer=layer,
        )
        taper.rotate(90)
        # Rotation makes the taper's bounding box wider than its centerline;
        # place it by its bbox so the silhouette stays explicit and stable.
        _place_bbox(
            taper,
            cx - taper_base_width / 2,
            body_y + body_width,
            cx + taper_base_width / 2,
            body_y + body_width + taper_length,
        )

    # Centered downward taper, wider at the body and narrow at its tip.
    lower = c << gf.components.taper(
        length=lower_taper_length,
        width1=lower_taper_tip_width,
        width2=taper_base_width,
        layer=layer,
    )
    lower.rotate(90)
    cx = body_x + body_length / 2
    _place_bbox(
        lower,
        cx - taper_base_width / 2,
        body_y - lower_taper_length,
        cx + taper_base_width / 2,
        body_y,
    )

    return c


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    component = device().copy()
    component.flatten()
    gds_path = out / "device.gds"
    component.write_gds(gds_path)
    # Required by the HOMI parametric-contract checks.
    with (out / "lengths.json").open("w") as f:
        json.dump(
            {"arms": {"reference": 0.0, "tunable_finger": delta_length},
             "delta_length_um": delta_length},
            f,
        )
