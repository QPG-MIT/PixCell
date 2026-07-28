"""Primitives-only reconstruction of the calibrated directional coupler."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Top-level, JEE-substitutable function-defining dimensions (um).
device_length = 18.0
guide_width = 0.646
center_width = 0.660
input_separation = 2.350
coupling_separation = 0.970
transfer_length = 0.500
transition_length = 8.750

LAYER = (1, 0)
HERE = Path(__file__).resolve().parent
GDS_PATH = HERE / "device.gds"
LENGTHS_PATH = HERE / "lengths.json"


def _half_separation(x: float) -> float:
    """Cosine-squared S-bend with a central parallel coupling section."""
    distance_from_center = max(0.0, abs(x - device_length / 2) - transfer_length / 2)
    t = min(1.0, distance_from_center / transition_length)
    return coupling_separation / 2 + (input_separation - coupling_separation) / 2 * np.sin(
        np.pi * t / 2
    ) ** 2


def _width(x: float) -> float:
    """The reference has a subtle, symmetric central guide widening."""
    width = guide_width + (center_width - guide_width) * np.sin(np.pi * x / device_length) ** 2
    return round(width / 0.002) * 0.002


def _make_guide(sign: float) -> tuple[gf.Component, gf.Path]:
    samples = 240
    xs = np.linspace(0.0, device_length, samples + 1)
    # The two centerlines are mirrored about the calibrated 1.5-um midplane.
    points = [(float(x), float(1.5 + sign * _half_separation(float(x)))) for x in xs]
    full_path = gf.Path(points)
    guide = gf.Component()
    # Piecewise primitive extrusion permits the shallow width profile without polygons.
    for left, right in zip(points[:-1], points[1:], strict=True):
        x_mid = (left[0] + right[0]) / 2
        guide.add_ref(gf.Path([left, right]).extrude(width=float(_width(x_mid)), layer=LAYER))
    return guide, full_path


@gf.cell
def directional_coupler() -> gf.Component:
    component = gf.Component()
    upper, _ = _make_guide(+1.0)
    lower, _ = _make_guide(-1.0)
    component.add_ref(upper)
    component.add_ref(lower)
    return component


if __name__ == "__main__":
    top = directional_coupler()
    # These are the actual two symmetric optical trajectories, measured from gf.Path.
    _, upper_path = _make_guide(+1.0)
    _, lower_path = _make_guide(-1.0)
    upper_length = float(upper_path.length())
    lower_length = float(lower_path.length())
    LENGTHS_PATH.write_text(
        json.dumps(
            {
                "arms": {"upper": upper_length, "lower": lower_length},
                "delta_length_um": abs(upper_length - lower_length),
            },
            indent=2,
        )
    )
    # Emit a top-level, reference-free GDS so external area measurement sees the geometry.
    top = top.copy()
    top.flatten()
    top.write_gds(GDS_PATH)
