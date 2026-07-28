from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf


# Parametric contract: all function-defining dimensions are live top-level values.
waveguide_width = 0.52
outer_half_width = 1.24
outer_half_height = 2.49
outer_flat_length = 1.16
inner_flat_length = 1.06
outer_curve_power = 2.0

bridge_width = 0.43
bridge_y_offset = 0.90
taper_length = 0.65
taper_angle_deg = 46.8
tip_width = 0.48
side_attach_x = 1.23
side_attach_y = 0.426
bridge_imbalance = 0.0

transfer_length = 0.89
slot_length = 0.33
slot_height = 0.55
coupling_gap = 0.11
slot_rail_width = 0.245

layer = (1, 0)
shape_slices = 240


def _filled_vertical_racetrack(
    *,
    half_width: float,
    half_height: float,
    flat_length: float,
) -> gf.Component:
    """Rounded solid assembled from a vertical stack of primitive tapers."""
    solid = gf.Component()
    flat_half = flat_length / 2

    def half_span(y: float) -> float:
        normalized_y = min(1.0, abs(y / half_height))
        bow = max(0.0, 1.0 - normalized_y**outer_curve_power) ** 0.5
        return round(flat_half + (half_width - flat_half) * bow, 3)

    step = 2 * half_height / shape_slices
    for index in range(shape_slices):
        y0 = -half_height + index * step
        y1 = y0 + step
        strip = gf.components.taper(
            length=step,
            width1=2 * half_span(y0),
            width2=2 * half_span(y1),
            layer=layer,
        )
        strip_ref = solid << strip
        strip_ref.drotate(90)
        strip_ref.dmove((0.0, y0))
    return solid


def _bridge_centerline(y_sign: float) -> gf.Path:
    """Measured centerline for one bridge, including both real taper spans."""
    angle = math.radians(taper_angle_deg)
    inner_x = side_attach_x - taper_length * math.cos(angle)
    inner_y = side_attach_y + taper_length * math.sin(angle)
    y = y_sign * inner_y
    outer_y = y_sign * side_attach_y
    return gf.Path(
        [
            (-side_attach_x, outer_y),
            (-inner_x, y),
            (inner_x, y),
            (side_attach_x, outer_y),
        ]
    )


def _add_taper(
    component: gf.Component,
    *,
    origin: tuple[float, float],
    angle_deg: float,
    width1: float,
    width2: float,
) -> None:
    taper = gf.components.taper(
        length=taper_length,
        width1=width1,
        width2=width2,
        layer=layer,
    )
    taper_ref = component << taper
    taper_ref.drotate(angle_deg)
    taper_ref.dmove(origin)


def _add_bridge(
    component: gf.Component,
    y_sign: float,
    imbalance: float = 0.0,
) -> tuple[gf.Path, gf.Path | None]:
    angle = math.radians(taper_angle_deg)
    inner_x = side_attach_x - taper_length * math.cos(angle)
    inner_y = side_attach_y + taper_length * math.sin(angle)
    y = y_sign * inner_y
    outer_y = y_sign * side_attach_y

    straight_path = gf.Path([(-inner_x, y), (inner_x, y)])
    component << gf.path.extrude(straight_path, width=bridge_width, layer=layer)

    left_angle = y_sign * taper_angle_deg
    right_angle = -y_sign * taper_angle_deg
    _add_taper(
        component,
        origin=(-side_attach_x, outer_y),
        angle_deg=left_angle,
        width1=tip_width,
        width2=bridge_width,
    )
    _add_taper(
        component,
        origin=(inner_x, y),
        angle_deg=right_angle,
        width1=bridge_width,
        width2=tip_width,
    )

    trim_path = None
    if y_sign > 0 and imbalance > 0:
        outer_edge_x = outer_half_width + waveguide_width / 2 - 0.002
        trim_path = gf.Path(
            [
                (outer_edge_x, outer_y),
                (outer_edge_x + imbalance, outer_y),
            ]
        )
        component << gf.path.extrude(trim_path, width=bridge_width, layer=layer)
    return _bridge_centerline(y_sign), trim_path


@gf.cell
def device() -> gf.Component:
    """Primitive-only compound slotted racetrack resonator."""
    outer_solid = _filled_vertical_racetrack(
        half_width=outer_half_width + waveguide_width / 2,
        half_height=outer_half_height + waveguide_width / 2,
        flat_length=outer_flat_length,
    )
    inner_void = _filled_vertical_racetrack(
        half_width=outer_half_width,
        half_height=outer_half_height - waveguide_width / 2,
        flat_length=inner_flat_length,
    )
    outer_ring = gf.boolean(A=outer_solid, B=inner_void, operation="not", layer=layer)

    material = gf.Component()
    material << outer_ring

    top_path, top_trim_path = _add_bridge(material, +1.0, bridge_imbalance)
    bottom_path, _ = _add_bridge(material, -1.0, 0.0)

    block_height = slot_height + 2 * slot_rail_width
    block = gf.components.rectangle(
        size=(transfer_length, block_height),
        layer=layer,
        centered=True,
    )
    top_block = material << block
    top_block.dcenter = (0.0, bridge_y_offset)
    bottom_block = material << block
    bottom_block.dcenter = (0.0, -bridge_y_offset)

    slots = gf.Component()
    slot_center_x = coupling_gap / 2 + slot_length / 2
    slot = gf.components.rectangle(
        size=(slot_length, slot_height),
        layer=layer,
        centered=True,
    )
    for y in (bridge_y_offset, -bridge_y_offset):
        for x in (-slot_center_x, slot_center_x):
            slot_ref = slots << slot
            slot_ref.dcenter = (x, y)

    carved = gf.boolean(A=material, B=slots, operation="not", layer=layer)
    result = gf.Component()
    result << carved

    top_length = float(top_path.length())
    if top_trim_path is not None:
        top_length += float(top_trim_path.length())
    bottom_length = float(bottom_path.length())
    lengths = {
        "arms": {
            "upper_bridge": top_length,
            "lower_bridge": bottom_length,
        },
        "delta_length_um": abs(top_length - bottom_length),
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(lengths, indent=2))
    return result


if __name__ == "__main__":
    device().write_gds(Path(__file__).with_name("device.gds"), with_metadata=False)
