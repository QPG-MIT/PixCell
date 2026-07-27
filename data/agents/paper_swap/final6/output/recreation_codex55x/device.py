from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Top-level tunables, intentionally plain assignments for HOMI/JEE substitution.
device_length = 4.7
device_width = 4.7
port_width = 0.236
port_straight = 0.50
taper_up_length = 0.92
taper_down_length = 0.93
lobe_width = 0.94
center_width = 0.62
taper_steps: int = 18
delta_length = 0.0


def _snap_width(width: float) -> float:
    return max(0.002, round(width / 0.002) * 0.002)


@gf.cell
def _transition_segment(
    length: float,
    width1: float,
    width2: float,
    steps: int = taper_steps,
    layer: tuple[int, int] = LAYER,
) -> gf.Component:
    c = gf.Component()
    seg_len = length / steps
    x = 0.0

    def eased_width(t: float) -> float:
        smooth_t = 0.5 - 0.5 * math.cos(math.pi * t)
        return width1 + (width2 - width1) * smooth_t

    for i in range(steps):
        w0 = _snap_width(eased_width(i / steps))
        w1 = _snap_width(eased_width((i + 1) / steps))
        ref = c << gf.components.taper(
            length=seg_len,
            width1=w0,
            width2=w1,
            layer=layer,
            with_bbox=False,
        )
        ref.dmovex(x)
        x += seg_len
    return c


@gf.cell
def _straight_segment(
    length: float,
    width: float,
    layer: tuple[int, int] = LAYER,
) -> gf.Component:
    xs = gf.cross_section.strip(width=width, layer=layer)
    return gf.components.straight(length=length, cross_section=xs)


@gf.cell
def _lobed_through_path(
    length: float = device_length,
    port_w: float = port_width,
    port_len: float = port_straight,
    up_len: float = taper_up_length,
    down_len: float = taper_down_length,
    lobe_w: float = lobe_width,
    center_w: float = center_width,
    imbalance: float = delta_length,
) -> gf.Component:
    c = gf.Component()
    x = 0.0

    sections = [
        (port_len, port_w, port_w),
        (up_len, port_w, lobe_w),
        (down_len, lobe_w, center_w),
        (down_len, center_w, lobe_w),
        (up_len, lobe_w, port_w),
        (port_len, port_w, port_w),
    ]

    for seg_len, w1, w2 in sections:
        ref = c << _transition_segment(length=seg_len, width1=w1, width2=w2)
        ref.dmovex(x)
        x += seg_len

    if imbalance > 0:
        ref = c << _straight_segment(length=imbalance, width=port_w)
        ref.dmovex(length)

    return c


@gf.cell
def recreate_device() -> gf.Component:
    c = gf.Component()

    horizontal = c << _lobed_through_path()
    vertical = c << _lobed_through_path(imbalance=0.0)
    vertical.drotate(90)
    vertical.dmove((device_length / 2, -device_width / 2))

    c.add_ports(horizontal.ports, prefix="h_")
    c.add_ports(vertical.ports, prefix="v_")
    return c


def write_lengths_json(path: Path) -> None:
    horizontal_length = device_length + max(delta_length, 0.0)
    vertical_length = device_width
    payload = {
        "arms": {
            "horizontal": horizontal_length,
            "vertical": vertical_length,
        },
        "delta_length_um": abs(horizontal_length - vertical_length),
    }
    path.write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    gf.clear_cache()
    component = recreate_device()
    component.write_gds("device.gds", with_metadata=False)
    write_lengths_json(Path("lengths.json"))
