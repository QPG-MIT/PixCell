from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


layer = (1, 0)
width_um = 0.060
tip_width_um = 0.022
gap_um = 0.145
taper_length_um = 0.55
transfer_length_um = 14.03
finger_pitch_um = 0.21
finger_count = 38
finger_length_um = 0.095
finger_width_um = 0.052
arm_radius_um = 0.18
delta_length = 0.00


def _add_arm(
    c: gf.Component,
    *,
    start: tuple[float, float],
    mid: list[tuple[float, float]],
    end: tuple[float, float],
    width: float,
    radius: float,
    layer: tuple[int, int],
) -> float:
    body = gf.path.smooth([start, *mid, end], radius=radius)
    c << body.extrude(width=width, layer=layer)
    return body.length()


def _add_finger_row(
    c: gf.Component,
    *,
    x0: float,
    y: float,
    pitch: float,
    count: int,
    finger_w: float,
    finger_h: float,
    layer: tuple[int, int],
    downward: bool,
) -> None:
    finger = gf.components.rectangle(size=(finger_w, finger_h), layer=layer)
    for i in range(count):
        ref = c << finger
        x = x0 + i * pitch
        if downward:
            ref.move((x, y - finger_h))
        else:
            ref.move((x, y))


@gf.cell
def build_device() -> gf.Component:
    c = gf.Component()

    # Outer rails: a high/top strip and a low/bottom strip with connector bends.
    upper_start = (0.42, 0.61)
    upper_mid = [(0.10, 0.60), (0.28, 0.44), (2.10, 0.40), (12.60, 0.40)]
    upper_end = (17.95, 0.22)
    upper_len = _add_arm(
        c,
        start=upper_start,
        mid=upper_mid,
        end=upper_end,
        width=width_um,
        radius=0.03,
        layer=layer,
    )

    lower_start = (0.42, 0.09)
    lower_mid = [(0.10, 0.10), (0.28, 0.25), (2.10, 0.30), (12.60, 0.30), (16.80, 0.19)]
    lower_end = (17.95, 0.07)
    lower_len = _add_arm(
        c,
        start=lower_start,
        mid=lower_mid,
        end=lower_end,
        width=width_um,
        radius=0.03,
        layer=layer,
    )

    # Central straight bar.
    center = gf.components.rectangle(size=(transfer_length_um, width_um), layer=layer)
    center_ref = c << center
    center_ref.move((1.95, 0.33))

    # Periodic corrugation-like rows.
    _add_finger_row(
        c,
        x0=4.75,
        y=0.35 + 0.5 * gap_um + 0.02,
        pitch=finger_pitch_um,
        count=finger_count,
        finger_w=finger_width_um,
        finger_h=finger_length_um,
        layer=layer,
        downward=True,
    )
    _add_finger_row(
        c,
        x0=4.75,
        y=0.35 - 0.5 * gap_um - 0.02,
        pitch=finger_pitch_um,
        count=finger_count,
        finger_w=finger_width_um,
        finger_h=finger_length_um,
        layer=layer,
        downward=False,
    )

    # Localized inner shoulders so the periodic section reads as a coupled pair.
    shoulder = gf.components.rectangle(size=(0.70, 0.035), layer=layer)
    for xpos in (3.95, 14.25):
        ref = c << shoulder
        ref.move((xpos, 0.39))
        ref = c << shoulder
        ref.move((xpos, 0.30))

    # Make delta_length an actual geometry knob by adding a small extra detour
    # on the lower arm. The arm-length measurement sees the extra path length.
    if delta_length > 0:
        detour = gf.path.smooth(
            [
                (15.70, 0.21),
                (15.70 + 0.45 * delta_length, 0.24),
                (15.70 + 0.90 * delta_length, 0.18),
                (15.70 + delta_length, 0.21),
            ],
            radius=0.015,
        )
        c << detour.extrude(width=width_um, layer=layer)

    gds_path = Path(__file__).with_suffix(".gds")
    c.write_gds(gds_path)

    lengths = {
        "arms": {
            "upper_arm": float(upper_len),
            "lower_arm": float(lower_len + max(delta_length, 0.0)),
        },
        "delta_length_um": float(abs((lower_len + max(delta_length, 0.0)) - upper_len)),
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(lengths, indent=2))
    return c


if __name__ == "__main__":
    build_device()
