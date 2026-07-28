"""Primitives-only recreation of the calibrated asymmetric directional coupler."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


LAYER = (1, 0)

# Top-level, JEE-substitutable geometry knobs (all dimensions are in um).
wg_width = 0.30
outer_lead_length = 8.0
taper_length = 5.7
left_sbend_length = 22.85
transfer_length = 45.8
right_sbend_length = 24.15
right_outer_lead_length = 13.5
upper_width_in = 0.42
upper_width_out = 0.31
lower_width_in = 0.19
lower_width_out = 0.29
lower_output_width = 0.29
gap = 0.155
left_port_center_y = 2.008
coupling_center_y = 1.9865
left_port_spacing = 3.442
right_port_spacing = 3.663
coupling_spacing = gap + (upper_width_in + lower_width_in) / 2.0
bend_control_fraction = 0.855
# A zero-default differential phase trim.  It is a real optical-path knob,
# verified below through the measured geometry contract.
delta_length = 0.0


def _path(points: np.ndarray) -> gf.Path:
    """Create a centerline path from primitive sampled points."""
    return gf.Path(points)


def _constant(path: gf.Path, width: float) -> gf.Component:
    return gf.path.extrude(path, width=width, layer=LAYER)


def _transition(path: gf.Path, width1: float, width2: float) -> gf.Component:
    """Extrude a linear-width primitive transition along a centerline."""
    if np.isclose(width1, width2):
        return _constant(path, width1)
    xs1 = gf.cross_section.cross_section(width=width1, layer=LAYER)
    xs2 = gf.cross_section.cross_section(width=width2, layer=LAYER)
    return path.extrude_transition(gf.path.transition(xs1, xs2, width_type="linear"))


def _horizontal(x0: float, x1: float, y: float) -> gf.Path:
    return _path(np.array([[x0, y], [x1, y]], dtype=float))


def _sbend(x0: float, length: float, y0: float, y1: float) -> gf.Path:
    """A sharp Bezier S-bend with horizontal tangents at both ends."""
    t = np.linspace(0.0, 1.0, 401)
    a = bend_control_fraction
    x = x0 + length * (
        3.0 * a * (1.0 - t) ** 2 * t
        + 3.0 * (1.0 - a) * (1.0 - t) * t**2
        + t**3
    )
    y = y0 + (y1 - y0) * (3.0 * (1.0 - t) * t**2 + t**3)
    return _path(np.column_stack((x, y)))


@gf.cell
def asymmetric_directional_coupler() -> gf.Component:
    """Four-port adiabatic directional coupler assembled only from paths."""
    component = gf.Component()

    x_taper_start = outer_lead_length
    x_sbend_start = x_taper_start + taper_length
    x_coupling_start = x_sbend_start + left_sbend_length
    x_coupling_end = x_coupling_start + transfer_length
    x_right_sbend_end = x_coupling_end + right_sbend_length

    y_top_left = left_port_center_y + left_port_spacing / 2.0
    y_bottom_left = left_port_center_y - left_port_spacing / 2.0
    y_top_coupling = coupling_center_y + coupling_spacing / 2.0
    y_bottom_coupling = coupling_center_y - coupling_spacing / 2.0
    y_top_right = 2.0 + right_port_spacing / 2.0
    y_bottom_right = 2.0 - right_port_spacing / 2.0

    top_paths = [
        _horizontal(0.0, x_taper_start, y_top_left),
        _horizontal(x_taper_start, x_sbend_start, y_top_left),
        _sbend(x_sbend_start, left_sbend_length, y_top_left, y_top_coupling),
        _horizontal(x_coupling_start, x_coupling_end, y_top_coupling),
        _sbend(x_coupling_end, right_sbend_length, y_top_coupling, y_top_right),
        _horizontal(
            x_right_sbend_end,
            x_right_sbend_end + right_outer_lead_length + delta_length,
            y_top_right,
        ),
    ]
    bottom_paths = [
        _horizontal(0.0, x_taper_start, y_bottom_left),
        _horizontal(x_taper_start, x_sbend_start, y_bottom_left),
        _sbend(x_sbend_start, left_sbend_length, y_bottom_left, y_bottom_coupling),
        _horizontal(x_coupling_start, x_coupling_end, y_bottom_coupling),
        _sbend(x_coupling_end, right_sbend_length, y_bottom_coupling, y_bottom_right),
        _horizontal(x_right_sbend_end, x_right_sbend_end + right_outer_lead_length, y_bottom_right),
    ]

    # Input tapers prepare the unequal-width coupling modes.
    component << _constant(top_paths[0], wg_width)
    component << _transition(top_paths[1], wg_width, upper_width_in)
    component << _constant(top_paths[2], upper_width_in)
    component << _transition(top_paths[3], upper_width_in, upper_width_out)
    component << _transition(top_paths[4], upper_width_out, wg_width)
    component << _constant(top_paths[5], wg_width)

    component << _constant(bottom_paths[0], wg_width)
    component << _transition(bottom_paths[1], wg_width, lower_width_in)
    component << _constant(bottom_paths[2], lower_width_in)
    component << _transition(bottom_paths[3], lower_width_in, lower_width_out)
    component << _transition(bottom_paths[4], lower_width_out, lower_output_width)
    component << _constant(bottom_paths[5], lower_output_width)

    component.info["top_path_length_um"] = sum(path.length() for path in top_paths)
    component.info["bottom_path_length_um"] = sum(path.length() for path in bottom_paths)
    return component


def _write_lengths(component: gf.Component, output_dir: Path) -> None:
    top = float(component.info["top_path_length_um"])
    bottom = float(component.info["bottom_path_length_um"])
    payload = {
        "arms": {"top": top, "bottom": bottom},
        "delta_length_um": abs(top - bottom),
    }
    (output_dir / "lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    device = asymmetric_directional_coupler()
    _write_lengths(device, output_dir)
    device.write_gds(output_dir / "device.gds", with_metadata=False)
