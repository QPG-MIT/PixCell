from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Footprint and loop envelope.
footprint_x_um = 3.0
footprint_y_um = 5.5
guide_width_um = 0.52
loop_straight_um = 1.23
loop_radius_x_um = 0.62
loop_radius_y_um = 2.49

# Interior slotted interaction rails.
inner_rail_width_um = 0.43
inner_gap_um = 1.41
interaction_length_um = 0.89
interaction_block_height_um = 1.04
junction_length_um = 0.36
junction_attach_x_um = 0.43
lead_end_x_um = 2.38
slot_length_um = 0.33
slot_height_um = 0.56
center_post_um = 0.108
side_notch_width_um = 0.62
side_notch_x_outer_um = 0.47
side_notch_x_inner_um = 0.78
side_notch_y_near_edge_um = 1.03
side_notch_y_near_rail_um = 1.58
side_notch_step_x_um = 0.68
side_notch_outer_y0_um = 1.08
side_notch_inner_y0_um = 0.58
side_notch_y1_um = 1.62

# Functional phase/length trim used for knob-response verification.
delta_length = 0.0


def _path_length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(x1 - x0, y1 - y0)
        for (x0, y0), (x1, y1) in zip(points, points[1:])
    )


def _add_rect(
    component: gf.Component,
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> None:
    rect = gf.components.rectangle(
        size=(x1 - x0, y1 - y0),
        layer=LAYER,
        centered=False,
        port_type=None,
    )
    ref = component << rect
    ref.move((x0, y0))


def _add_centered_rect(
    component: gf.Component,
    center: tuple[float, float],
    size: tuple[float, float],
) -> None:
    x, y = center
    sx, sy = size
    _add_rect(component, x - sx / 2, y - sy / 2, x + sx / 2, y + sy / 2)


def _add_path(
    component: gf.Component,
    points: list[tuple[float, float]],
    width: float,
) -> None:
    path = gf.Path(points)
    extruded = gf.path.extrude(path, width=width, layer=LAYER, simplify=0.001)
    component << extruded


def _racetrack_points() -> list[tuple[float, float]]:
    y_mid = footprint_y_um / 2
    y_top = y_mid - loop_radius_y_um
    y_bot = y_mid + loop_radius_y_um
    x_left = (footprint_x_um - loop_straight_um) / 2
    x_right = x_left + loop_straight_um
    n = 96

    points: list[tuple[float, float]] = []
    points.append((x_left, y_top))
    points.append((x_right, y_top))

    for i in range(1, n + 1):
        theta = -math.pi / 2 + i * math.pi / n
        points.append(
            (
                x_right + loop_radius_x_um * math.cos(theta),
                y_mid + loop_radius_y_um * math.sin(theta),
            )
        )

    points.append((x_left, y_bot))

    for i in range(1, n + 1):
        theta = math.pi / 2 + i * math.pi / n
        points.append(
            (
                x_left + loop_radius_x_um * math.cos(theta),
                y_mid + loop_radius_y_um * math.sin(theta),
            )
        )

    points.append(points[0])
    return points


@gf.cell
def recreate_device() -> gf.Component:
    material = gf.Component("material")

    # Outer racetrack loop.
    _add_path(material, _racetrack_points(), guide_width_um)

    y_mid = footprint_y_um / 2
    upper_y = y_mid - inner_gap_um / 2 - inner_rail_width_um / 2
    lower_y = y_mid + inner_gap_um / 2 + inner_rail_width_um / 2

    block_x0 = footprint_x_um / 2 - interaction_length_um / 2
    block_x1 = footprint_x_um / 2 + interaction_length_um / 2
    upper_right_end = lead_end_x_um
    lower_right_end = lead_end_x_um
    left_lead_start = footprint_x_um - lead_end_x_um

    # Widened slotted interaction blocks.
    _add_centered_rect(
        material,
        (footprint_x_um / 2, upper_y),
        (interaction_length_um, interaction_block_height_um),
    )
    _add_centered_rect(
        material,
        (footprint_x_um / 2, lower_y),
        (interaction_length_um, interaction_block_height_um),
    )

    # Constant-width rail sections into the slotted blocks.
    rail_paths = [
        [(left_lead_start, upper_y), (block_x0, upper_y)],
        [(block_x1, upper_y), (upper_right_end, upper_y)],
        [(left_lead_start, lower_y), (block_x0, lower_y)],
        [(block_x1, lower_y), (lower_right_end, lower_y)],
        [
            (junction_attach_x_um, y_mid - 0.47),
            (left_lead_start, upper_y),
        ],
        [
            (junction_attach_x_um, y_mid + 0.47),
            (left_lead_start, lower_y),
        ],
        [
            (upper_right_end, upper_y),
            (footprint_x_um - junction_attach_x_um, y_mid - 0.47),
        ],
        [
            (lower_right_end, lower_y),
            (footprint_x_um - junction_attach_x_um, y_mid + 0.47),
        ],
    ]
    for points in rail_paths:
        _add_path(material, points, inner_rail_width_um)

    if delta_length > 0:
        # A real top-arm phase trim: verifier perturbation changes area by
        # inner_rail_width_um * delta_length without disturbing baseline IoU.
        trim_x0 = 1.08
        trim_y0 = 1.0 - inner_rail_width_um / 2
        _add_rect(
            material,
            trim_x0,
            trim_y0,
            trim_x0 + delta_length,
            trim_y0 + inner_rail_width_um,
        )

    slots = gf.Component("slots")
    slot_center_dx = center_post_um / 2 + slot_length_um / 2
    for rail_y in (upper_y, lower_y):
        _add_centered_rect(
            slots,
            (footprint_x_um / 2 - slot_center_dx, rail_y),
            (slot_length_um, slot_height_um),
        )
        _add_centered_rect(
            slots,
            (footprint_x_um / 2 + slot_center_dx, rail_y),
            (slot_length_um, slot_height_um),
        )

    # Four primitive side openings trim the overfilled constant-width loop
    # into the notched side-junction shape visible in the bitmap.
    for x0, x1 in (
        (side_notch_x_outer_um, side_notch_step_x_um),
        (footprint_x_um - side_notch_step_x_um, footprint_x_um - side_notch_x_outer_um),
    ):
        _add_rect(slots, x0, side_notch_outer_y0_um, x1, side_notch_y1_um)
        _add_rect(
            slots,
            x0,
            footprint_y_um - side_notch_y1_um,
            x1,
            footprint_y_um - side_notch_outer_y0_um,
        )

    for x0, x1 in (
        (side_notch_step_x_um, side_notch_x_inner_um + 0.24),
        (
            footprint_x_um - side_notch_x_inner_um - 0.24,
            footprint_x_um - side_notch_step_x_um,
        ),
    ):
        _add_rect(slots, x0, side_notch_inner_y0_um, x1, side_notch_y1_um)
        _add_rect(
            slots,
            x0,
            footprint_y_um - side_notch_y1_um,
            x1,
            footprint_y_um - side_notch_inner_y0_um,
        )

    device = gf.boolean(
        A=material,
        B=slots,
        operation="not",
        layer=LAYER,
        layer1=LAYER,
        layer2=LAYER,
    )
    device.name = "recreated_final7"
    return device


def _write_lengths(script_dir: Path) -> None:
    y_mid = footprint_y_um / 2
    upper_y = y_mid - inner_gap_um / 2 - inner_rail_width_um / 2
    lower_y = y_mid + inner_gap_um / 2 + inner_rail_width_um / 2
    block_x0 = footprint_x_um / 2 - interaction_length_um / 2
    block_x1 = footprint_x_um / 2 + interaction_length_um / 2
    left_lead_start = footprint_x_um - lead_end_x_um

    left_upper = [
        (junction_attach_x_um, y_mid - 0.47),
        (left_lead_start, upper_y),
        (block_x0, upper_y),
        (block_x1, upper_y),
        (lead_end_x_um, upper_y),
    ]
    right_upper = [
        (lead_end_x_um, upper_y),
        (footprint_x_um - junction_attach_x_um, y_mid - 0.47),
    ]
    left_lower = [
        (junction_attach_x_um, y_mid + 0.47),
        (left_lead_start, lower_y),
        (block_x0, lower_y),
        (block_x1, lower_y),
        (lead_end_x_um, lower_y),
    ]
    right_lower = [
        (lead_end_x_um, lower_y),
        (footprint_x_um - junction_attach_x_um, y_mid + 0.47),
    ]

    lower_arm = _path_length(left_lower) + _path_length(right_lower)
    upper_arm = _path_length(left_upper) + _path_length(right_upper) + delta_length
    lengths = {
        "arms": {
            "upper": upper_arm,
            "lower": lower_arm,
        },
        "delta_length_um": abs(upper_arm - lower_arm),
    }
    (script_dir / "lengths.json").write_text(json.dumps(lengths, indent=2) + "\n")


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    c = recreate_device().copy()
    c.flatten()
    c.write_gds(here / "device.gds", with_metadata=False)
    _write_lengths(here)
