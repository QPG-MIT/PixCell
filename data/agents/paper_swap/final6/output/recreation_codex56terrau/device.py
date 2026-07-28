"""Parametric primitives-only recreation of the supplied four-port crossing."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Top-level tunables: these are intentionally simple numeric assignments so
# HOMI/JEE can substitute them directly during a later retargeting pass.
footprint_length = 4.7
footprint_width = 4.7
waveguide_width = 0.236
lead_length = 0.548
petal_length = 1.802
max_petal_width = 0.928
center_waist_width = 0.235
taper_exponent = 0.70
phase_arm_extension = 0.0

layer = (1, 0)
output_dir = Path(__file__).resolve().parent


def petal_width(position: np.ndarray) -> np.ndarray:
    """Smooth symmetric lead-to-petal-to-waist width profile in microns."""
    x = np.asarray(position, dtype=float) * footprint_length
    distance_from_nearest_port = np.minimum(x, footprint_length - x)
    normalized_petal_position = np.clip(
        (distance_from_nearest_port - lead_length) / petal_length, 0.0, 1.0
    )
    bulge = np.sin(np.pi * normalized_petal_position) ** taper_exponent
    local_waist = center_waist_width + (waveguide_width - center_waist_width) * (
        1.0 - normalized_petal_position
    )
    return local_waist + (max_petal_width - local_waist) * bulge


def arm_cross_section() -> gf.CrossSection:
    """The single material section used by every path primitive."""
    section = gf.Section(
        width=waveguide_width,
        width_function=petal_width,
        layer=layer,
    )
    return gf.CrossSection(sections=(section,))


def lead_cross_section() -> gf.CrossSection:
    """Fixed-width cross-section for a one-port path-length adjustment."""
    section = gf.Section(width=waveguide_width, layer=layer)
    return gf.CrossSection(sections=(section,))


@gf.cell
def horizontal_arm() -> gf.Component:
    """One full straight-through crossing axis with two adiabatic petals."""
    centerline = gf.path.straight(length=footprint_length, npoints=1001)
    return centerline.extrude(cross_section=arm_cross_section())


@gf.cell
def crossing() -> gf.Component:
    """Assemble horizontal and orthogonal primitive-path arms."""
    component = gf.Component()
    component << horizontal_arm()

    vertical = component << horizontal_arm()
    vertical.drotate(90)
    vertical.dmove((footprint_length / 2, -footprint_width / 2))

    # This live path-length knob extends the right-hand port only.  At its
    # zero baseline the recreated geometry remains fourfold symmetric; when
    # retuned it is a real one-guide phase/path-length adjustment.
    if phase_arm_extension > 0:
        extension_path = gf.path.straight(length=phase_arm_extension, npoints=2)
        extension = component << extension_path.extrude(cross_section=lead_cross_section())
        extension.dmove((footprint_length, 0))
    return component


if __name__ == "__main__":
    device = crossing()
    horizontal_length = footprint_length + phase_arm_extension
    vertical_length = footprint_length
    (output_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {"horizontal": horizontal_length, "vertical": vertical_length},
                "delta_length_um": abs(horizontal_length - vertical_length),
                "crossing": {
                    "lead_length_um": lead_length,
                    "petal_length_um": petal_length,
                    "max_petal_width_um": max_petal_width,
                },
            },
            indent=2,
        )
    )
    device.write_gds(output_dir / "device.gds", with_metadata=False)
