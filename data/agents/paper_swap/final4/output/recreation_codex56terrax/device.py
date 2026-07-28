"""Parametric primitives-only recreation of the final4 directional coupler."""

from __future__ import annotations

import json
from pathlib import Path as FilePath

import gdsfactory as gf
import numpy as np


# Function-defining geometric tunables (all dimensions are micrometres).
coupler_length = 18.0
footprint_width = 3.0
wg_width = 0.65
coupling_gap = 0.30
port_straight_length = 0.90
s_bend_length = 7.10
interaction_length = 2.00
transition_shape_points = 201
# A differential output extension is a real phase-trim knob.  It is zero for
# this symmetric image recreation, but retains a measurable physical response.
delta_length = 0.0
layer = (1, 0)


def _raised_cosine_s_bend_points() -> tuple[np.ndarray, np.ndarray]:
    """Return mirror-symmetric centreline samples for the two guide paths."""
    constructed_length = (
        2.0 * port_straight_length + 2.0 * s_bend_length + interaction_length
    )
    if not np.isclose(constructed_length, coupler_length):
        raise ValueError("coupler_length must equal the sum of its parametric regions")

    x = np.linspace(0.0, coupler_length, transition_shape_points)
    centre_y = footprint_width / 2.0
    port_separation = footprint_width - wg_width
    central_separation = coupling_gap + wg_width
    inward_shift = (port_separation - central_separation) / 2.0

    approach_start = port_straight_length
    approach_end = approach_start + s_bend_length
    depart_start = approach_end + interaction_length
    depart_end = coupler_length - port_straight_length

    fraction = np.zeros_like(x)
    approaching = (x > approach_start) & (x < approach_end)
    fraction[approaching] = 0.5 * (
        1.0 - np.cos(np.pi * (x[approaching] - approach_start) / s_bend_length)
    )
    fraction[(x >= approach_end) & (x <= depart_start)] = 1.0
    departing = (x > depart_start) & (x < depart_end)
    fraction[departing] = 0.5 * (
        1.0 + np.cos(np.pi * (x[departing] - depart_start) / s_bend_length)
    )

    upper_y = centre_y + port_separation / 2.0 - inward_shift * fraction
    lower_y = centre_y - port_separation / 2.0 + inward_shift * fraction
    return np.column_stack((x, upper_y)), np.column_stack((x, lower_y))


def _centreline_length(points: np.ndarray) -> float:
    return float(np.sum(np.hypot(np.diff(points[:, 0]), np.diff(points[:, 1]))))


@gf.cell
def directional_coupler() -> gf.Component:
    """Two matched raised-cosine S-bends forming a directional coupler."""
    c = gf.Component()
    upper_points, lower_points = _raised_cosine_s_bend_points()

    # The phase-trim extension is a straight physical continuation of the top
    # guide; at the calibrated value (zero) both arms are exactly symmetric.
    if delta_length > 0.0:
        upper_points = np.vstack(
            (upper_points, (coupler_length + delta_length, upper_points[-1, 1]))
        )

    upper_path = gf.Path(upper_points)
    lower_path = gf.Path(lower_points)
    c << gf.path.extrude(upper_path, width=wg_width, layer=layer)
    c << gf.path.extrude(lower_path, width=wg_width, layer=layer)
    return c


if __name__ == "__main__":
    component = directional_coupler()
    output_dir = FilePath(__file__).parent
    # Write a flattened primitives-only export cell.  Keeping this explicit
    # also lets the deterministic knob-area audit inspect layer-(1, 0)
    # polygons without following GDSFactory's cache metadata references.
    export = gf.Component("device_export")
    export << component
    export.flatten()
    export.write_gds(output_dir / "device.gds")

    upper_points, lower_points = _raised_cosine_s_bend_points()
    upper_length = _centreline_length(upper_points) + delta_length
    lower_length = _centreline_length(lower_points)
    (output_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {"upper": upper_length, "lower": lower_length},
                "delta_length_um": abs(upper_length - lower_length),
                "coupler": {
                    "length_um": interaction_length,
                    "gap_um": coupling_gap,
                    "width_um": wg_width,
                },
            },
            indent=2,
        )
    )
