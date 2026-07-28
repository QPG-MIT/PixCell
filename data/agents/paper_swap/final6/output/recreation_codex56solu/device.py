"""Parametric primitive reconstruction of a four-port multimode crossing."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Function-defining dimensions (um), kept as live top-level tunables.
guide_width = 0.230
lobe_length = 1.807
lobe_max_width = 0.906
lobe_center_offset = 0.861
horizontal_path_length = 4.7
vertical_path_length = 4.7
path_samples: int = 801

LAYER = (1, 0)


def make_axis_path(axis_length: float) -> gf.Path:
    """Return a densely sampled, centered straight path in physical microns."""
    path = gf.path.straight(length=axis_length, npoints=path_samples)
    path.dmovex(-axis_length / 2)
    return path


def extrude_lobed_axis(path: gf.Path, axis_length: float) -> gf.Component:
    """Extrude a narrow guide unioned analytically with two elliptical lobes."""
    semi_axis = lobe_length / 2

    def width_profile(t: np.ndarray) -> np.ndarray:
        coordinate = (np.asarray(t) - 0.5) * axis_length
        normalized = (np.abs(coordinate) - lobe_center_offset) / semi_axis
        ellipse_term = np.sqrt(np.clip(1.0 - normalized**2, 0.0, 1.0))
        ellipse_width = lobe_max_width * ellipse_term
        return np.maximum(guide_width, ellipse_width)

    section = gf.Section(
        width=guide_width,
        width_function=width_profile,
        layer=LAYER,
        port_names=("o1", "o2"),
        name="core",
    )
    cross_section = gf.CrossSection(sections=(section,))
    return gf.path.extrude(path, cross_section=cross_section)


@gf.cell
def device() -> gf.Component:
    """Assemble two orthogonal, congruent lobed guide extrusions."""
    component = gf.Component()

    horizontal_path = make_axis_path(horizontal_path_length)
    vertical_path = make_axis_path(vertical_path_length)
    vertical_path.rotate(90)

    horizontal = component << extrude_lobed_axis(horizontal_path, horizontal_path_length)
    vertical = component << extrude_lobed_axis(vertical_path, vertical_path_length)

    component.add_ports(horizontal.ports, prefix="h_")
    component.add_ports(vertical.ports, prefix="v_")
    component.info["horizontal_path_length_um"] = float(horizontal_path.length())
    component.info["vertical_path_length_um"] = float(vertical_path.length())
    return component


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    crossing = device()
    crossing.write_gds(output_dir / "device.gds", with_metadata=False)

    horizontal_length = float(crossing.info["horizontal_path_length_um"])
    vertical_length = float(crossing.info["vertical_path_length_um"])
    measured = {
        "arms": {
            "horizontal": horizontal_length,
            "vertical": vertical_length,
        },
        "delta_length_um": abs(horizontal_length - vertical_length),
    }
    (output_dir / "lengths.json").write_text(json.dumps(measured, indent=2) + "\n")
