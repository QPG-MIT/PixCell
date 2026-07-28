"""Primitive-only recreation of the supplied two-guide directional coupler."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Function-defining tunables.  The upper coupling length is the declared
# differential-length knob used by homi.spec_optimization.verify_knob_response.
coupling_length = 57.0
coupling_length_reference = 57.0
coupling_gap = 0.16
bend_radius = 8.0
wg_width = 0.22
lower_wg_width = 0.38
port_width = 0.29
port_separation = 3.46
right_port_separation = 3.66
left_port_length = 10.0
right_port_length = 17.0
left_bend_span = 21.0
right_bend_span = 15.0
center_y_upper = 1.69
center_y_lower = center_y_upper + coupling_gap + (wg_width + lower_wg_width) / 2
left_y_upper = 0.21
right_y_upper = 0.09
left_y_lower = left_y_upper + port_separation
right_y_lower = right_y_upper + right_port_separation
path_samples = 81


def _smoothstep_segment(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    profile_t: np.ndarray,
    profile_f: np.ndarray,
    samples: int = path_samples,
) -> np.ndarray:
    """Return a measured-profile, horizontal-tangent S-bend centerline."""
    t = np.linspace(0.0, 1.0, samples)
    radius_scale = np.clip(bend_radius / 8.0, 0.75, 1.25)
    adjusted_t = np.clip(0.5 + (profile_t - 0.5) / radius_scale, 0.0, 1.0)
    interval = np.clip(np.searchsorted(adjusted_t, t, side="right") - 1, 0, len(adjusted_t) - 2)
    local_t = (t - adjusted_t[interval]) / np.maximum(
        adjusted_t[interval + 1] - adjusted_t[interval], 1e-9
    )
    eased = local_t * local_t * (3.0 - 2.0 * local_t)
    fraction = profile_f[interval] + (profile_f[interval + 1] - profile_f[interval]) * eased
    return np.column_stack((x0 + (x1 - x0) * t, y0 + (y1 - y0) * fraction))


def _route(
    *,
    y_left: float,
    y_center: float,
    y_right: float,
    coupling_length_value: float,
    screen_top: bool,
) -> gf.Path:
    """Build one routed guide as a gf.Path centerline."""
    coupling_start = left_port_length + left_bend_span
    coupling_end = coupling_start + coupling_length_value
    right_bend_end = coupling_end + right_bend_span
    right_end = right_bend_end + right_port_length

    left_profile_t = np.array([0.0, 0.30, 0.46, 0.60, 0.76, 0.90, 1.0])
    left_profile_f = np.array([0.0, 0.0, 0.04, 0.17, 0.72, 0.92, 1.0])
    right_profile_t = np.array([0.0, 0.10, 0.30, 0.50, 0.70, 0.90, 1.0])
    right_profile_f = np.array([0.0, 0.05, 0.20, 0.75, 0.92, 0.99, 1.0])

    left_straight = np.array(
        [[0.0, y_left], [left_port_length, y_left]], dtype=float
    )
    left_bend = _smoothstep_segment(
        left_port_length,
        y_left,
        coupling_start,
        y_center,
        left_profile_t,
        left_profile_f,
    )
    center = np.array([[coupling_start, y_center], [coupling_end, y_center]])
    right_bend = _smoothstep_segment(
        coupling_end,
        y_center,
        right_bend_end,
        y_right,
        right_profile_t,
        right_profile_f,
    )
    right_straight = np.array([[right_bend_end, y_right], [right_end, y_right]])

    points = np.concatenate(
        [
            left_straight,
            left_bend[1:],
            center[1:],
            right_bend[1:],
            right_straight[1:],
        ]
    )
    return gf.Path(points)


def _width_section(path: gf.Path, *, narrow: float, wide: float) -> gf.CrossSection:
    """Make a strip section that widens only through the coupling centerline."""
    points = path.points
    segment_lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.concatenate(([0.0], np.cumsum(segment_lengths)))
    total = cumulative[-1]

    # The route is assembled in five pieces: the port straight, left S-bend,
    # coupling straight, right S-bend, and port straight.
    left_transition_s = cumulative[1]
    left_width_end_s = cumulative[1 + int(0.25 * (path_samples - 1))]
    center_end_s = cumulative[1 + (path_samples - 1) + 1]
    if total <= 0 or center_end_s >= total:
        center_end_s = min(total, 0.75 * total)

    def width_function(t: np.ndarray) -> np.ndarray:
        s = np.asarray(t, dtype=float) * total
        out = np.full_like(s, narrow)
        ramp_in = np.clip((s - left_transition_s) / max(left_width_end_s - left_transition_s, 1e-9), 0.0, 1.0)
        ramp_out = np.clip((s - center_end_s) / max(total - center_end_s, 1e-9), 0.0, 1.0)
        ease_in = ramp_in * ramp_in * (3.0 - 2.0 * ramp_in)
        ease_out = ramp_out * ramp_out * (3.0 - 2.0 * ramp_out)
        out = narrow + (wide - narrow) * ease_in
        return out * (1.0 - ease_out) + narrow * ease_out

    section = gf.Section(
        width=narrow,
        layer=(1, 0),
        port_names=("o1", "o2"),
        width_function=width_function,
    )
    return gf.CrossSection(sections=(section,))


@gf.cell
def directional_coupler() -> gf.Component:
    """Two mirrored, tapered guides assembled from path extrusions."""
    component = gf.Component()
    upper_path = _route(
        y_left=left_y_upper,
        y_center=center_y_upper,
        y_right=right_y_upper,
        coupling_length_value=coupling_length,
        screen_top=False,
    )
    lower_path = _route(
        y_left=left_y_lower,
        y_center=center_y_lower,
        y_right=right_y_lower,
        coupling_length_value=coupling_length_reference,
        screen_top=True,
    )

    component.add_ref(
        gf.path.extrude(
            upper_path,
            cross_section=_width_section(upper_path, narrow=port_width, wide=wg_width),
        )
    )
    component.add_ref(
        gf.path.extrude(
            lower_path,
            cross_section=_width_section(
                lower_path, narrow=port_width, wide=lower_wg_width
            ),
        )
    )
    return component


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    device = directional_coupler()
    gds_path = output_dir / "device.gds"
    device.write_gds(gds_path, with_metadata=False)
    upper = _route(
        y_left=left_y_upper,
        y_center=center_y_upper,
        y_right=right_y_upper,
        coupling_length_value=coupling_length,
        screen_top=False,
    )
    lower = _route(
        y_left=left_y_lower,
        y_center=center_y_lower,
        y_right=right_y_lower,
        coupling_length_value=coupling_length_reference,
        screen_top=True,
    )
    upper_length = float(upper.length())
    lower_length = float(lower.length())
    (output_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {"upper": upper_length, "lower": lower_length},
                "delta_length_um": abs(upper_length - lower_length),
            },
            indent=2,
        )
        + "\n"
    )
