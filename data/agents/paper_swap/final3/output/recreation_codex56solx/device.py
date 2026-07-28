from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Function-defining, conductor/JEE-substitutable tunables (all dimensions in um).
wg_width = 0.29
wide_tip_width = 0.42
narrow_tip_width = 0.16
input_taper_length = 18.0
output_taper_length = 84.0
coupling_gap = 0.17
coupling_length = 54.0
bend_length = 15.0
input_pitch = 3.45
output_pitch = 3.66
left_lead_length = 18.0
right_lead_length = 18.0
upper_left_bend_width = 1.18
lower_left_bend_width = 0.41
upper_right_bend_width = 0.98
lower_right_bend_width = 0.85

# Small center-axis offsets reproduce the source drawing's measured vertical placement.
input_axis_y = 0.012
coupling_axis_y = -0.01
output_axis_y = 0.0

layer = (1, 0)
curve_samples = 81


def _smoothstep_segment(
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    samples: int,
) -> np.ndarray:
    """Cubic, horizontal-tangent S-transition sampled as a gf.Path primitive."""
    u = np.linspace(0.0, 1.0, samples)
    blend = u * u * (3.0 - 2.0 * u)
    return np.column_stack((x0 + (x1 - x0) * u, y0 + (y1 - y0) * blend))


def _centerline(*, upper: bool) -> gf.Path:
    sign = 1.0 if upper else -1.0
    y_in = input_axis_y + sign * input_pitch / 2.0
    y_coupled = coupling_axis_y + sign * (
        coupling_gap / 2.0 + (wide_tip_width + narrow_tip_width) / 4.0
    )
    y_out = output_axis_y + sign * output_pitch / 2.0

    x_bend_in = left_lead_length
    x_coupled_in = x_bend_in + bend_length
    x_coupled_out = x_coupled_in + coupling_length
    x_bend_out = x_coupled_out + bend_length
    x_end = x_bend_out + right_lead_length

    points = [
        np.array([[0.0, y_in], [x_bend_in, y_in]]),
        _smoothstep_segment(
            x_bend_in, x_coupled_in, y_in, y_coupled, curve_samples
        )[1:],
        np.array([[x_coupled_out, y_coupled]]),
        _smoothstep_segment(
            x_coupled_out, x_bend_out, y_coupled, y_out, curve_samples
        )[1:],
        np.array([[x_end, y_out]]),
    ]
    return gf.Path(np.concatenate(points))


def _tapered_cross_section(
    path: gf.Path,
    *,
    upper: bool,
) -> gf.CrossSection:
    path_length = path.length()
    coupled_in = left_lead_length + bend_length
    coupled_out = coupled_in + coupling_length
    bend_out = coupled_out + bend_length
    end = bend_out + right_lead_length

    if upper:
        intermediate_width = wide_tip_width
        left_peak = upper_left_bend_width
        right_peak = upper_right_bend_width
        widths = np.array(
            [
                wg_width,
                intermediate_width,
                intermediate_width + 0.09,
                left_peak,
                left_peak - 0.10,
                intermediate_width + 0.07,
                intermediate_width,
                wg_width + 0.05,
                wg_width + 0.09,
                right_peak,
                right_peak - 0.10,
                wg_width + 0.08,
                wg_width + 0.03,
                wg_width,
            ]
        )
    else:
        intermediate_width = narrow_tip_width
        left_peak = lower_left_bend_width
        right_peak = lower_right_bend_width
        widths = np.array(
            [
                wg_width,
                intermediate_width,
                intermediate_width + 0.06,
                left_peak,
                left_peak - 0.08,
                intermediate_width + 0.06,
                intermediate_width + 0.03,
                wg_width + 0.01,
                wg_width + 0.05,
                right_peak - 0.06,
                right_peak,
                wg_width + 0.05,
                wg_width + 0.01,
                wg_width,
            ]
        )

    distances = np.array(
        [
            0.0,
            input_taper_length,
            left_lead_length + 0.2 * bend_length,
            left_lead_length + 0.4 * bend_length,
            left_lead_length + 0.6 * bend_length,
            left_lead_length + 0.8 * bend_length,
            coupled_in,
            coupled_out,
            coupled_out + 0.2 * bend_length,
            coupled_out + 0.4 * bend_length,
            coupled_out + 0.6 * bend_length,
            coupled_out + 0.8 * bend_length,
            min(input_taper_length + output_taper_length, bend_out),
            end,
        ]
    )

    def width_profile(t: np.ndarray) -> np.ndarray:
        distance_um = np.asarray(t) * path_length
        return np.interp(distance_um, distances, widths)

    section = gf.Section(
        width=wg_width,
        width_function=width_profile,
        layer=layer,
        port_names=("o1", "o2"),
    )
    return gf.CrossSection(sections=(section,))


@gf.cell
def adiabatic_directional_coupler() -> gf.Component:
    component = gf.Component()
    upper_path = _centerline(upper=True)
    lower_path = _centerline(upper=False)
    upper = gf.path.extrude(
        upper_path,
        cross_section=_tapered_cross_section(upper_path, upper=True),
    )
    lower = gf.path.extrude(
        lower_path,
        cross_section=_tapered_cross_section(lower_path, upper=False),
    )
    component.add_ref(upper)
    component.add_ref(lower)
    return component


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    upper_path = _centerline(upper=True)
    lower_path = _centerline(upper=False)
    upper_length = upper_path.length()
    lower_length = lower_path.length()
    lengths = {
        "coupler": {
            "length_um": coupling_length,
            "gap_um": coupling_gap,
            "width_um": wg_width,
        },
        "arms": {
            "upper": upper_length,
            "lower": lower_length,
        },
        "delta_length_um": abs(upper_length - lower_length),
    }
    (output_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    adiabatic_directional_coupler().write_gds(
        output_dir / "device.gds", with_metadata=False
    )
