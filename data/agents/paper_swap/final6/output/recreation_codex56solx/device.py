from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


wg_width = 0.236
lobe_length = 1.870
lobe_peak_width = 0.928
center_overlap = 0.160
port_straight_length = 0.557
other_port_straight_length = 0.557
lobe_samples: int = 161

LAYER = (1, 0)


def elliptical_width(t: np.ndarray) -> np.ndarray:
    """Elliptical full-width profile, sampled along a straight centerline."""
    normalized = 2.0 * np.asarray(t) - 1.0
    return lobe_peak_width * np.sqrt(np.maximum(0.0, 1.0 - normalized**2))


def extruded_straight(length: float, width: float) -> tuple[gf.Component, gf.Path]:
    """Return a path-derived straight primitive and its measured centerline."""
    path = gf.path.straight(length=length)
    return gf.path.extrude(path, width=width, layer=LAYER), path


def elliptical_lobe() -> tuple[gf.Component, gf.Path]:
    """Return one lens lobe built only from a width-varying path extrusion."""
    path = gf.path.straight(length=lobe_length, npoints=lobe_samples)
    section = gf.Section(
        width=lobe_peak_width,
        width_function=elliptical_width,
        layer=LAYER,
        port_names=(None, None),
    )
    cross_section = gf.CrossSection(sections=(section,))
    return gf.path.extrude(path, cross_section=cross_section), path


@gf.cell
def crossing() -> gf.Component:
    """Fourfold-symmetric adiabatic crossing assembled from path primitives."""
    component = gf.Component()
    lobe, _ = elliptical_lobe()

    outer_tip = lobe_length - center_overlap / 2.0

    left_lobe = component.add_ref(lobe)
    left_lobe.dmove((-outer_tip, 0.0))

    right_lobe = component.add_ref(lobe)
    right_lobe.dmove((-center_overlap / 2.0, 0.0))

    bottom_lobe = component.add_ref(lobe)
    bottom_lobe.drotate(90)
    bottom_lobe.dmove((0.0, -outer_tip))

    top_lobe = component.add_ref(lobe)
    top_lobe.drotate(90)
    top_lobe.dmove((0.0, -center_overlap / 2.0))

    left_access, _ = extruded_straight(port_straight_length, wg_width)
    left = component.add_ref(left_access)
    left.dmove((-outer_tip - port_straight_length, 0.0))

    other_access, _ = extruded_straight(other_port_straight_length, wg_width)

    right = component.add_ref(other_access)
    right.dmove((outer_tip, 0.0))

    bottom = component.add_ref(other_access)
    bottom.drotate(90)
    bottom.dmove((0.0, -outer_tip - other_port_straight_length))

    top = component.add_ref(other_access)
    top.drotate(90)
    top.dmove((0.0, outer_tip))

    component.flatten()
    return component


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    device = crossing()
    device.write_gds(output_dir / "device.gds", with_metadata=False)

    _, lobe_path = elliptical_lobe()
    _, input_access_path = extruded_straight(port_straight_length, wg_width)
    fixed_route_length = 2.0 * lobe_path.length()
    variable_route_length = fixed_route_length + input_access_path.length()
    (output_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {
                    "fixed_crossing_route": fixed_route_length,
                    "input_extended_route": variable_route_length,
                },
                "delta_length_um": abs(variable_route_length - fixed_route_length),
            },
            indent=2,
        )
    )
