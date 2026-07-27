from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Footprint and absolute-placement controls.
footprint_length_um = 3.0
footprint_width_um = 5.5

# Outer closed guide/racetrack.
outer_rx_um = 1.50
outer_ry_um = 2.75
outer_exponent_um = 3.0
inner_rx_um = 0.98
inner_ry_um = 2.24
inner_exponent_um = 5.0
outer_stripes: int = 120

# Inner arm and access geometry.
guide_width_um = 0.42
arm_y_um = 0.88
access_x_um = 0.44
access_edge_y_um = 0.65
access_mid_y_um = 0.82
body_height_um = 1.02
transfer_length_um = 0.88

# Slot/window geometry inside the widened interaction sections.
slot_length_um = 0.34
slot_height_um = 0.45
slot_gap_um = 0.11

# Real differential-length knob. Baseline is symmetric; perturbing this adds
# actual guide area on the upper arm and is reported through lengths.json.
delta_length = 0.0


def _path_component(points: list[tuple[float, float]], width: float) -> gf.Component:
    path = gf.Path(points)
    return path.extrude(width=width, layer=LAYER, simplify=0.001)


def _filled_superellipse(
    rx: float,
    ry: float,
    exponent: float,
    stripes: int,
) -> gf.Component:
    cx = footprint_length_um / 2
    c = gf.Component()
    dy = 2 * ry / stripes
    for index in range(stripes):
        y = -ry + (index + 0.5) * dy
        normalized = min(abs(y) / ry, 1.0)
        half_width = rx * max(0.0, 1 - normalized**exponent) ** (1 / exponent)
        if half_width <= 0:
            continue
        c << _rect((2 * half_width, dy * 1.01), (cx, y))
    return c


def _outer_loop() -> gf.Component:
    outer = _filled_superellipse(
        outer_rx_um,
        outer_ry_um,
        outer_exponent_um,
        outer_stripes,
    )
    inner = _filled_superellipse(
        inner_rx_um,
        inner_ry_um,
        inner_exponent_um,
        outer_stripes,
    )
    return gf.boolean(outer, inner, operation="A-B", layer=LAYER)


def _rect(size: tuple[float, float], center: tuple[float, float]) -> gf.Component:
    c = gf.Component()
    ref = c << gf.components.rectangle(size=size, layer=LAYER, centered=True)
    ref.move(center)
    return c


def _interaction_body(y: float) -> gf.Component:
    cx = footprint_length_um / 2
    body = _rect((transfer_length_um, body_height_um), (cx, y))

    slot_dx = slot_gap_um / 2 + slot_length_um / 2
    holes = gf.Component()
    holes << _rect((slot_length_um, slot_height_um), (cx - slot_dx, y))
    holes << _rect((slot_length_um, slot_height_um), (cx + slot_dx, y))

    return gf.boolean(body, holes, operation="A-B", layer=LAYER)


def _access_guides() -> gf.Component:
    cx = footprint_length_um / 2
    body_left = cx - transfer_length_um / 2
    body_right = cx + transfer_length_um / 2
    left_touch_x = access_x_um
    right_touch_x = footprint_length_um - access_x_um

    c = gf.Component()
    for sign in (1, -1):
        y = sign * arm_y_um
        mid_y = sign * access_mid_y_um
        edge_y = sign * access_edge_y_um
        c << _path_component(
            [(left_touch_x, edge_y), (0.72, mid_y), (body_left, y)],
            guide_width_um,
        )
        c << _path_component(
            [(body_right, y), (2.28, mid_y), (right_touch_x, edge_y)],
            guide_width_um,
        )
    return c


def _delta_length_guide() -> gf.Component:
    c = gf.Component()
    if delta_length <= 0:
        return c
    cx = footprint_length_um / 2
    body_right = cx + transfer_length_um / 2
    y = arm_y_um
    c << _path_component(
        [(body_right, y), (body_right + delta_length, y)],
        guide_width_um,
    )
    return c


def _union_components(parts: list[gf.Component]) -> gf.Component:
    result = parts[0]
    for part in parts[1:]:
        result = gf.boolean(result, part, operation="or", layer=LAYER)
    return result


def _polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(x1 - x0, y1 - y0)
        for (x0, y0), (x1, y1) in zip(points, points[1:])
    )


@gf.cell
def recreate_device() -> gf.Component:
    parts = [
        _outer_loop(),
        _access_guides(),
        _interaction_body(arm_y_um),
        _interaction_body(-arm_y_um),
        _delta_length_guide(),
    ]
    return _union_components(parts)


def _write_lengths() -> None:
    cx = footprint_length_um / 2
    body_left = cx - transfer_length_um / 2
    body_right = cx + transfer_length_um / 2
    left_touch_x = access_x_um
    right_touch_x = footprint_length_um - access_x_um
    upper_left = [
        (left_touch_x, access_edge_y_um),
        (0.72, access_mid_y_um),
        (body_left, arm_y_um),
    ]
    upper_right = [
        (body_right, arm_y_um),
        (2.28, access_mid_y_um),
        (right_touch_x, access_edge_y_um),
    ]
    base_arm = (
        _polyline_length(upper_left)
        + transfer_length_um
        + _polyline_length(upper_right)
    )
    upper = base_arm + max(delta_length, 0.0)
    lower = base_arm
    payload = {
        "arms": {
            "upper": upper,
            "lower": lower
        },
        "delta_length_um": abs(upper - lower)
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    gf.clear_cache()
    component = recreate_device()
    component.write_gds(Path(__file__).with_name("recreation.gds"), with_metadata=False)
    _write_lengths()
