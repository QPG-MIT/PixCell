from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)
GDS_NAME = "device.gds"

# Footprint in um from footprint.json
footprint_x = 3.0
footprint_y = 5.5

# Outer loop
outer_track_width = 0.52
outer_corner_radius = 0.98

# Inner bodies
body_x0 = 0.63
body_x1 = 2.37
body_height = 1.03
upper_body_y0 = 3.15
lower_body_y0 = 1.32

# Slots
slot_width = 0.325
slot_height = 0.425
slot_pitch = 0.435
slot_center_offset = 0.22

# Necks and tapers
neck_width = 0.43
delta_length = 0.08
stub_length = 0.18
taper_length = 0.11
guide_width = 0.12
shoulder_width = 0.72


def rounded_perimeter() -> gf.Component:
    c = gf.Component("rounded_perimeter")
    r = outer_corner_radius
    w = outer_track_width
    h_straight = footprint_x - 2 * r - w
    v_straight = footprint_y - 2 * r - w
    if h_straight <= 0 or v_straight <= 0:
        raise ValueError("outer_corner_radius too large for footprint")

    p = gf.Path([(r + w / 2, w / 2)])
    p.append(gf.path.straight(length=h_straight))
    p.append(gf.path.arc(radius=r, angle=90))
    p.append(gf.path.straight(length=v_straight))
    p.append(gf.path.arc(radius=r, angle=90))
    p.append(gf.path.straight(length=h_straight))
    p.append(gf.path.arc(radius=r, angle=90))
    p.append(gf.path.straight(length=v_straight))
    p.append(gf.path.arc(radius=r, angle=90))

    ring = p.extrude(width=w, layer=LAYER)
    c << ring
    return c


def body_with_slots(name: str, y0: float) -> gf.Component:
    c = gf.Component(name)
    y1 = y0 + body_height
    body = gf.components.rectangle(size=(body_x1 - body_x0, body_height), layer=LAYER)
    body_ref = c << body
    body_ref.move((body_x0, y0))

    hole_y0 = y0 + (body_height - slot_height) / 2
    hole1_x0 = body_x0 + 0.49
    hole2_x0 = hole1_x0 + slot_pitch
    hole1 = gf.components.rectangle(size=(slot_width, slot_height), layer=LAYER)
    hole2 = gf.components.rectangle(size=(slot_width, slot_height), layer=LAYER)

    cut = gf.Component(f"{name}_cut")
    h1 = cut << hole1
    h1.move((hole1_x0, hole_y0))
    h2 = cut << hole2
    h2.move((hole2_x0, hole_y0))

    slotted = gf.boolean(A=c, B=cut, operation="not", layer=LAYER)
    out = gf.Component(f"{name}_slotted")
    out << slotted
    return out


def place_connector_blocks(c: gf.Component, y_center: float, body_side_x: float, extra_straight: float, direction: str) -> None:
    if direction not in {"left", "right"}:
        raise ValueError("direction must be left or right")

    neck = gf.components.rectangle(size=(stub_length + extra_straight, neck_width), layer=LAYER)
    shoulder = gf.components.rectangle(size=(taper_length, shoulder_width), layer=LAYER)

    if direction == "left":
        neck_ref = c << neck
        neck_ref.move((body_side_x - taper_length - stub_length - extra_straight, y_center - neck_width / 2))
        shoulder_ref = c << shoulder
        shoulder_ref.move((body_side_x - taper_length, y_center - shoulder_width / 2))
    else:
        shoulder_ref = c << shoulder
        shoulder_ref.move((body_side_x, y_center - shoulder_width / 2))
        neck_ref = c << neck
        neck_ref.move((body_side_x + taper_length, y_center - neck_width / 2))


def build_arm_paths() -> tuple[gf.Path, gf.Path]:
    upper_y = upper_body_y0 + body_height / 2
    lower_y = lower_body_y0 + body_height / 2

    upper = gf.Path([(0.18, upper_y)])
    upper.append(gf.path.straight(length=body_x0 - 0.18))
    upper.append(gf.path.straight(length=delta_length))
    upper.append(gf.path.straight(length=body_x1 - body_x0))
    upper.append(gf.path.straight(length=footprint_x - body_x1 - 0.18))

    lower = gf.Path([(0.18, lower_y)])
    lower.append(gf.path.straight(length=body_x0 - 0.18))
    lower.append(gf.path.straight(length=body_x1 - body_x0))
    lower.append(gf.path.straight(length=footprint_x - body_x1 - 0.18))
    return upper, lower


def place_delta_tabs(c: gf.Component) -> None:
    tab_height = delta_length / 2
    tab = gf.components.rectangle(size=(guide_width, tab_height), layer=LAYER)
    y_top = upper_body_y0 + body_height
    left_tab = c << tab
    left_tab.move((body_x0 + 0.32, y_top))
    right_tab = c << tab
    right_tab.move((body_x1 - 0.32 - guide_width, y_top))


@gf.cell(check_instances=False)
def device() -> gf.Component:
    c = gf.Component("device")
    c << rounded_perimeter()

    upper = c << body_with_slots("upper", upper_body_y0)
    lower = c << body_with_slots("lower", lower_body_y0)
    upper.movex(0)
    lower.movex(0)

    upper_y = upper_body_y0 + body_height / 2
    lower_y = lower_body_y0 + body_height / 2

    place_connector_blocks(c, y_center=upper_y, body_side_x=body_x0, extra_straight=delta_length / 2, direction="left")
    place_connector_blocks(c, y_center=lower_y, body_side_x=body_x0, extra_straight=0.0, direction="left")
    place_connector_blocks(c, y_center=upper_y, body_side_x=body_x1, extra_straight=delta_length / 2, direction="right")
    place_connector_blocks(c, y_center=lower_y, body_side_x=body_x1, extra_straight=0.0, direction="right")
    place_delta_tabs(c)

    upper_path, lower_path = build_arm_paths()
    c << upper_path.extrude(width=guide_width, layer=LAYER)
    c << lower_path.extrude(width=guide_width, layer=LAYER)

    lengths = {
        "arms": {
            "upper": round(upper_path.length(), 6),
            "lower": round(lower_path.length(), 6),
        },
        "delta_length_um": round(abs(upper_path.length() - lower_path.length()), 6),
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(lengths, indent=2))

    c.flatten()
    return c


if __name__ == "__main__":
    gf.clear_cache()
    component = device()
    component.write_gds(Path(__file__).with_name(GDS_NAME), with_metadata=False)
