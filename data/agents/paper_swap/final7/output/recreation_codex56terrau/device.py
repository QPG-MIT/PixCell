"""Primitives-only recreation of the final7 slotted racetrack cell.

The material is a broad closed resonant guide with two mirrored, windowed
transfer rails.  All fabrication geometry is on layer (1, 0).
"""

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Live, top-level geometric contract (all dimensions are microns).
guide_width = 0.52
outer_radius_x = 1.24
outer_radius_y = 2.49
superellipse_exponent = 3.40
rail_length = 0.89
rail_height = 1.03
rail_center_offset = 0.91
window_width = 0.33
window_height = 0.56
window_gap = 0.11
bridge_width = 0.50
bridge_ring_x = 0.51
bridge_ring_y_offset = 0.64
bridge_rail_x = 0.90
bridge_rail_y_offset = 1.12
delta_length = 0.05

layer = (1, 0)
center_x = 1.50
center_y = 2.75
ellipse_points = 256


def superellipse_centerline() -> gf.Path:
    """Returns the closed centerline of the outer resonant guide."""
    theta = np.linspace(0.0, 2.0 * np.pi, ellipse_points, endpoint=False)
    cosine = np.cos(theta)
    sine = np.sin(theta)
    exponent = 2.0 / superellipse_exponent
    points = np.column_stack(
        (
            center_x + outer_radius_x * np.sign(cosine) * np.abs(cosine) ** exponent,
            center_y + outer_radius_y * np.sign(sine) * np.abs(sine) ** exponent,
        )
    )
    return gf.Path(np.vstack((points, points[0])))


def add_rectangle(component: gf.Component, size: tuple[float, float], origin: tuple[float, float]) -> None:
    """Adds one layer-(1, 0) primitive rectangle at its lower-left origin."""
    reference = component.add_ref(gf.components.rectangle(size=size, layer=layer))
    reference.dmove(origin)


@gf.cell
def outer_resonator() -> gf.Component:
    """Closed broad guide formed by extruding a parametric centerline."""
    return superellipse_centerline().extrude(layer=layer, width=guide_width)


@gf.cell
def slotted_rail(rail_center_y: float) -> gf.Component:
    """A perforated transfer rail assembled only from rectangles."""
    component = gf.Component()
    x0 = center_x - rail_length / 2.0
    y0 = rail_center_y - rail_height / 2.0
    x_left_window = center_x - window_gap / 2.0 - window_width
    x_right_window = center_x + window_gap / 2.0
    y_window = rail_center_y - window_height / 2.0

    # Full-width top and bottom bars plus three vertical separators leave two
    # precisely rectangular apertures without raw polygon emission.
    add_rectangle(component, (rail_length, y_window - y0), (x0, y0))
    add_rectangle(
        component,
        (rail_length, y0 + rail_height - (y_window + window_height)),
        (x0, y_window + window_height),
    )
    add_rectangle(component, (x_left_window - x0, window_height), (x0, y_window))
    add_rectangle(
        component,
        (x_right_window - (x_left_window + window_width), window_height),
        (x_left_window + window_width, y_window),
    )
    add_rectangle(
        component,
        (x0 + rail_length - (x_right_window + window_width), window_height),
        (x_right_window + window_width, y_window),
    )
    return component


@gf.cell
def bridge(start: tuple[float, float], end: tuple[float, float]) -> gf.Component:
    """Broad diagonal primitive connecting a rail to the outer guide."""
    return gf.Path(np.asarray((start, end), dtype=float)).extrude(layer=layer, width=bridge_width)


@gf.cell
def phase_trim() -> gf.Component:
    """One real guide-width branch extension controlled by delta_length."""
    start = np.asarray((center_x + outer_radius_x, center_y), dtype=float)
    end = start + np.asarray((delta_length, 0.0), dtype=float)
    return gf.Path(np.asarray((start, end), dtype=float)).extrude(layer=layer, width=guide_width)


@gf.cell
def device() -> gf.Component:
    """Assembles the symmetric slotted resonator from primitive cells."""
    component = gf.Component()
    component.add_ref(outer_resonator())

    top_rail_y = center_y + rail_center_offset
    bottom_rail_y = center_y - rail_center_offset
    component.add_ref(slotted_rail(top_rail_y))
    component.add_ref(slotted_rail(bottom_rail_y))

    component.add_ref(
        bridge(
            (bridge_ring_x, center_y + bridge_ring_y_offset),
            (bridge_rail_x, center_y + bridge_rail_y_offset),
        )
    )
    component.add_ref(
        bridge(
            (2.0 * center_x - bridge_ring_x, center_y + bridge_ring_y_offset),
            (2.0 * center_x - bridge_rail_x, center_y + bridge_rail_y_offset),
        )
    )
    component.add_ref(
        bridge(
            (bridge_ring_x, center_y - bridge_ring_y_offset),
            (bridge_rail_x, center_y - bridge_rail_y_offset),
        )
    )
    component.add_ref(
        bridge(
            (2.0 * center_x - bridge_ring_x, center_y - bridge_ring_y_offset),
            (2.0 * center_x - bridge_rail_x, center_y - bridge_rail_y_offset),
        )
    )
    component.add_ref(phase_trim())
    return component


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    output_gds = output_dir / "device.gds"
    built = device()

    # These two centerline paths define the reference and phase-trimmed
    # resonant branches.  The reported difference is derived, never typed in.
    reference_arm = superellipse_centerline().length()
    trim_path = gf.Path(
        np.asarray(
            ((center_x + outer_radius_x, center_y), (center_x + outer_radius_x + delta_length, center_y)),
            dtype=float,
        )
    )
    tuned_arm = reference_arm + trim_path.length()
    lengths = {
        "arms": {"reference": reference_arm, "phase_trimmed": tuned_arm},
        "delta_length_um": abs(tuned_arm - reference_arm),
    }
    (output_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    built.write_gds(output_gds, with_metadata=False)
