from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Parametric device contract: all function-defining dimensions are top-level,
# numeric assignments in micrometres.
wg_width = 0.66
upper_tip_width = 0.66
lower_tip_width = 0.66
gap = 0.29
transfer_length = 1.0
lead_length = 0.75
approach_length = 7.75
input_taper_length = 7.75
output_taper_length = 7.75
port_pitch = 2.34
phase_trim_length = 0.0
center_y = 1.5
path_samples = 721

layer = (1, 0)


# Dimensionless measured shape of one approach. The physical separation is
# still governed by port_pitch, gap, tip widths, lead/approach/transfer lengths.
_PROFILE_U = np.array(
    [0.0, 0.032, 0.097, 0.161, 0.290, 0.419, 0.548, 0.677, 0.806, 0.935, 1.0]
)
_PROFILE_FAR_FRACTION = np.array(
    [1.0, 0.995, 0.971, 0.947, 0.794, 0.558, 0.327, 0.164, 0.073, 0.014, 0.0]
)


def _separation_fraction(x: np.ndarray, body_length: float) -> np.ndarray:
    """Return 1 at isolated ports and 0 through the interaction region."""
    distance_from_edge = np.minimum(x, body_length - x)
    u = np.clip((distance_from_edge - lead_length) / approach_length, 0.0, 1.0)
    fraction = np.interp(u, _PROFILE_U, _PROFILE_FAR_FRACTION)
    return np.where(distance_from_edge <= lead_length, 1.0, fraction)


def _make_paths() -> tuple[gf.Path, gf.Path]:
    body_length = 2.0 * lead_length + 2.0 * approach_length + transfer_length
    x = np.linspace(0.0, body_length, path_samples)
    fraction = _separation_fraction(x, body_length)

    interaction_pitch = gap + (upper_tip_width + lower_tip_width) / 2.0
    pitch = interaction_pitch + (port_pitch - interaction_pitch) * fraction

    upper_points = np.column_stack((x, center_y + pitch / 2.0))
    lower_points = np.column_stack((x, center_y - pitch / 2.0))
    if phase_trim_length > 0.0:
        upper_points = np.vstack(
            (upper_points, [body_length + phase_trim_length, upper_points[-1, 1]])
        )

    return gf.Path(upper_points), gf.Path(lower_points)


def _width_profile(
    path_length: float,
    port_width: float,
    interaction_width: float,
):
    """Sinusoidal port-to-tip and tip-to-port width transition."""

    def width_at(t):
        distance = np.asarray(t, dtype=float) * path_length
        width = np.full_like(distance, interaction_width, dtype=float)

        left = distance < input_taper_length
        left_u = np.clip(distance / input_taper_length, 0.0, 1.0)
        left_blend = 0.5 - 0.5 * np.cos(np.pi * left_u)
        width = np.where(
            left,
            port_width + (interaction_width - port_width) * left_blend,
            width,
        )

        right_distance = path_length - distance
        right = right_distance < output_taper_length
        right_u = np.clip(right_distance / output_taper_length, 0.0, 1.0)
        right_blend = 0.5 - 0.5 * np.cos(np.pi * right_u)
        width = np.where(
            right,
            port_width + (interaction_width - port_width) * right_blend,
            width,
        )
        return width

    return width_at


def _extrude_guide(path: gf.Path, port_width: float, tip_width: float):
    section = gf.Section(
        width=port_width,
        width_function=_width_profile(path.length(), port_width, tip_width),
        layer=layer,
        port_names=("o1", "o2"),
    )
    cross_section = gf.CrossSection(sections=(section,))
    return gf.path.extrude(path, cross_section=cross_section)


@gf.cell
def adiabatic_directional_coupler() -> gf.Component:
    component = gf.Component()
    upper_path, lower_path = _make_paths()
    component.add_ref(_extrude_guide(upper_path, wg_width, upper_tip_width))
    component.add_ref(_extrude_guide(lower_path, wg_width, lower_tip_width))
    return component


if __name__ == "__main__":
    device = adiabatic_directional_coupler()
    upper_path, lower_path = _make_paths()
    upper_length = float(upper_path.length())
    lower_length = float(lower_path.length())
    payload = {
        "arms": {
            "upper": upper_length,
            "lower": lower_length,
        },
        "delta_length_um": abs(upper_length - lower_length),
        "coupler": {
            "length_um": transfer_length,
            "gap_um": gap,
            "width_um": (upper_tip_width + lower_tip_width) / 2.0,
        },
    }
    Path("lengths.json").write_text(json.dumps(payload, indent=2))
    device.write_gds("device.gds", with_metadata=False)
