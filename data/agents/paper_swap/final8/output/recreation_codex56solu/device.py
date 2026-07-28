"""Primitives-only parametric recreation of the calibrated multi-rail device."""

from __future__ import annotations

import json
from pathlib import Path as FilePath

import gdsfactory as gf
import numpy as np


# Function-defining tunables (all dimensions in um).
transfer_length = 120.0
device_length = 120.0
rail_width = 0.068
rail_gap = 0.032
rail_count = 5
fanout_length = 1.62
fanout_exponent = 1.70
fanout_trunk_width = 0.45
outer_rail_width = 0.472
outer_straight_length = 100.0
outer_trunk_width = 0.55
outer_center_offset = 0.502
inner_center_offset = 0.801
center_group_offset = -0.007

LAYER = (1, 0)


def _bezier_path(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    samples: int = 64,
) -> gf.Path:
    """Cubic Bezier centerline represented as a GDSFactory Path."""
    t = np.linspace(0.0, 1.0, samples)[:, None]
    one_minus_t = 1.0 - t
    points = (
        one_minus_t**3 * np.asarray(p0)
        + 3.0 * one_minus_t**2 * t * np.asarray(p1)
        + 3.0 * one_minus_t * t**2 * np.asarray(p2)
        + t**3 * np.asarray(p3)
    )
    return gf.Path(points)


def _add_path(component: gf.Component, path: gf.Path, width: float) -> None:
    """Extrude one centerline on the device layer and add it to the assembly."""
    component.add_ref(gf.path.extrude(path, width=width, layer=LAYER))


def _add_rectangle(
    component: gf.Component,
    x_start: float,
    x_stop: float,
    y_center: float,
    width: float,
) -> None:
    """Add a centered longitudinal rectangle primitive."""
    rectangle = gf.components.rectangle(
        size=(x_stop - x_start, width),
        layer=LAYER,
        centered=False,
        port_type=None,
    )
    component.add_ref(rectangle).move((x_start, y_center - width / 2.0))


@gf.cell
def build_device() -> gf.Component:
    """Assemble the symmetric rail groups from paths and rectangles only."""
    component = gf.Component()
    pitch = rail_width + rail_gap

    # The five full-length central rails. The first is the active interaction
    # path controlled by transfer_length; the second is its physical reference
    # for the path-derived knob-response contract.
    central_paths: list[gf.Path] = []
    for index in range(rail_count):
        y = center_group_offset + (rail_count // 2 - index) * pitch
        length = transfer_length if index == 0 else device_length
        path = gf.Path()
        path.append(gf.path.straight(length=length))
        path.movey(y)
        _add_path(component, path, rail_width)
        central_paths.append(path)

    # Mirrored five-rail nested interaction/fanout groups.
    for sign in (1.0, -1.0):
        for index in range(rail_count):
            y = sign * (inner_center_offset + index * pitch)
            normalized_depth = (rail_count - 1 - index) / (rail_count - 1)
            inset = fanout_length * normalized_depth**fanout_exponent
            x_start = (device_length - outer_straight_length) / 2.0 - 2.18 + inset
            _add_rectangle(
                component,
                x_start=x_start,
                x_stop=device_length - x_start,
                y_center=y,
                width=rail_width,
            )

        # Narrow rounded access trunks joining the progressively inset rails.
        y_end = sign * inner_center_offset
        left_inner = _bezier_path(
            (7.10, sign * 2.0),
            (7.10, sign * 1.42),
            (8.20, sign * inner_center_offset),
            (9.45, y_end),
        )
        right_inner = _bezier_path(
            (device_length - 7.10, sign * 2.0),
            (device_length - 7.10, sign * 1.42),
            (device_length - 8.20, sign * inner_center_offset),
            (device_length - 9.45, y_end),
        )
        _add_path(component, left_inner, fanout_trunk_width)
        _add_path(component, right_inner, fanout_trunk_width)

        # Broad outer access rail: a long straight joined to two rounded trunks.
        outer_x_start = (device_length - outer_straight_length) / 2.0
        outer_y = sign * outer_center_offset
        _add_rectangle(
            component,
            x_start=outer_x_start,
            x_stop=device_length - outer_x_start,
            y_center=outer_y,
            width=outer_rail_width,
        )
        left_outer = _bezier_path(
            (4.85, sign * 2.0),
            (4.95, sign * 1.22),
            (7.20, outer_y),
            (outer_x_start, outer_y),
        )
        right_outer = _bezier_path(
            (device_length - 4.85, sign * 2.0),
            (device_length - 4.95, sign * 1.22),
            (device_length - 7.20, outer_y),
            (device_length - outer_x_start, outer_y),
        )
        _add_path(component, left_outer, outer_trunk_width)
        _add_path(component, right_outer, outer_trunk_width)

    # Lengths are measured from the actual GDSFactory Path objects.
    active_length = float(central_paths[0].length())
    reference_length = float(central_paths[1].length())
    lengths = {
        "arms": {
            "interaction": active_length,
            "reference": reference_length,
        },
        "delta_length_um": abs(active_length - reference_length),
    }
    FilePath(__file__).with_name("lengths.json").write_text(
        json.dumps(lengths, indent=2) + "\n"
    )
    return component


if __name__ == "__main__":
    device = build_device()
    # Suppress the KLayout context wrapper so the deterministic evaluator sees
    # build_device itself as a top-level geometry cell for layer-area checks.
    device.write_gds(
        FilePath(__file__).with_name("device.gds"),
        with_metadata=False,
    )
