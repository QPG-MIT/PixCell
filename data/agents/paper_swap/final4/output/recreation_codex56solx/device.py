from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Function-defining, top-level tunables (all dimensions are in micrometers).
wg_width = 0.65
tip_width = 0.65
port_pitch = 2.35
coupling_gap = 0.30
approach_length = 8.50
taper_length = 8.50
transfer_length = 1.00
differential_length = 0.00
layer = (1, 0)


# A normalized, smooth approach profile read from the supplied silhouette.
# The table describes a centerline (not polygon vertices); all physical scale
# and function-defining dimensions remain controlled by the tunables above.
_PROFILE_T = np.array(
    [0.0, 1 / 8.5, 2 / 8.5, 3 / 8.5, 4 / 8.5, 5 / 8.5, 6 / 8.5, 7 / 8.5, 8 / 8.5, 1.0]
)
_PROFILE_Y = np.array([0.0, 0.015, 0.058, 0.216, 0.447, 0.677, 0.840, 0.931, 0.988, 1.0])


def _profile(t: np.ndarray) -> np.ndarray:
    """C1 cubic-Hermite interpolation through the normalized approach profile."""
    t = np.clip(np.asarray(t, dtype=float), 0.0, 1.0)
    slopes = np.empty_like(_PROFILE_Y)
    slopes[0] = 0.0
    slopes[-1] = 0.0
    slopes[1:-1] = (
        (_PROFILE_Y[2:] - _PROFILE_Y[:-2])
        / (_PROFILE_T[2:] - _PROFILE_T[:-2])
    )

    indices = np.searchsorted(_PROFILE_T, t, side="right") - 1
    indices = np.clip(indices, 0, len(_PROFILE_T) - 2)
    x0 = _PROFILE_T[indices]
    x1 = _PROFILE_T[indices + 1]
    y0 = _PROFILE_Y[indices]
    y1 = _PROFILE_Y[indices + 1]
    m0 = slopes[indices]
    m1 = slopes[indices + 1]
    h = x1 - x0
    u = (t - x0) / h

    h00 = 2 * u**3 - 3 * u**2 + 1
    h10 = u**3 - 2 * u**2 + u
    h01 = -2 * u**3 + 3 * u**2
    h11 = u**3 - u**2
    return h00 * y0 + h10 * h * m0 + h01 * y1 + h11 * h * m1


def _center_y(x: np.ndarray, *, upper: bool) -> np.ndarray:
    """Mirrored guide center for arbitrary x within the balanced coupler."""
    x = np.asarray(x, dtype=float)
    base_length = 2 * approach_length + transfer_length
    t = np.where(
        x <= approach_length,
        x / approach_length,
        np.where(
            x <= approach_length + transfer_length,
            1.0,
            (base_length - x) / approach_length,
        ),
    )
    progress = _profile(t)

    device_center = 0.5 * (wg_width + port_pitch)
    outer_upper = 0.5 * wg_width
    outer_lower = outer_upper + port_pitch
    central_spacing = coupling_gap + tip_width
    central_upper = device_center - 0.5 * central_spacing
    central_lower = device_center + 0.5 * central_spacing

    if upper:
        return outer_upper + (central_upper - outer_upper) * progress
    return outer_lower + (central_lower - outer_lower) * progress


def _sampled_path(
    x_start: float,
    x_stop: float,
    *,
    upper: bool,
    samples_per_um: float = 24.0,
) -> gf.Path:
    count = max(2, int(np.ceil(abs(x_stop - x_start) * samples_per_um)) + 1)
    x = np.linspace(x_start, x_stop, count)
    return gf.Path(np.column_stack([x, _center_y(x, upper=upper)]))


def _full_path(*, upper: bool) -> gf.Path:
    base_length = 2 * approach_length + transfer_length
    x = np.linspace(0.0, base_length, int(np.ceil(base_length * 24.0)) + 1)
    points = np.column_stack([x, _center_y(x, upper=upper)])
    if upper and differential_length > 0:
        points = np.vstack(
            [points, [base_length + differential_length, float(_center_y(np.array([base_length]), upper=True)[0])]]
        )
    return gf.Path(points)


def _add_extruded(
    component: gf.Component,
    path: gf.Path,
    *,
    width_start: float,
    width_stop: float,
) -> None:
    xs_start = gf.cross_section.cross_section(width=width_start, layer=layer)
    if abs(width_start - width_stop) < 1e-12:
        component.add_ref(path.extrude(cross_section=xs_start))
        return
    xs_stop = gf.cross_section.cross_section(width=width_stop, layer=layer)
    transition = gf.path.transition(
        cross_section1=xs_start,
        cross_section2=xs_stop,
        width_type="sine",
    )
    component.add_ref(gf.path.extrude_transition(path, transition))


def _add_guide(component: gf.Component, *, upper: bool) -> None:
    base_length = 2 * approach_length + transfer_length
    taper = min(max(taper_length, 1e-6), approach_length)
    left_taper_start = approach_length - taper
    right_taper_stop = approach_length + transfer_length + taper

    if left_taper_start > 1e-9:
        _add_extruded(
            component,
            _sampled_path(0.0, left_taper_start, upper=upper),
            width_start=wg_width,
            width_stop=wg_width,
        )
    _add_extruded(
        component,
        _sampled_path(left_taper_start, approach_length, upper=upper),
        width_start=wg_width,
        width_stop=tip_width,
    )

    _add_extruded(
        component,
        _sampled_path(
            approach_length,
            approach_length + transfer_length,
            upper=upper,
        ),
        width_start=tip_width,
        width_stop=tip_width,
    )

    _add_extruded(
        component,
        _sampled_path(
            approach_length + transfer_length,
            right_taper_stop,
            upper=upper,
        ),
        width_start=tip_width,
        width_stop=wg_width,
    )
    if right_taper_stop < base_length - 1e-9:
        _add_extruded(
            component,
            _sampled_path(right_taper_stop, base_length, upper=upper),
            width_start=wg_width,
            width_stop=wg_width,
        )

    if upper and differential_length > 0:
        extension = gf.path.straight(length=differential_length)
        extension.move((0.0, 0.0), (base_length, float(_center_y(np.array([base_length]), upper=True)[0])))
        _add_extruded(
            component,
            extension,
            width_start=wg_width,
            width_stop=wg_width,
        )


@gf.cell
def device() -> gf.Component:
    component = gf.Component()
    _add_guide(component, upper=True)
    _add_guide(component, upper=False)
    return component


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    upper_path = _full_path(upper=True)
    lower_path = _full_path(upper=False)
    upper_length = float(upper_path.length())
    lower_length = float(lower_path.length())

    component = device()
    component.write_gds(output_dir / "device.gds", with_metadata=False)
    (output_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {
                    "upper": upper_length,
                    "lower": lower_length,
                },
                "delta_length_um": abs(upper_length - lower_length),
                "coupler": {
                    "length_um": transfer_length,
                    "gap_um": coupling_gap,
                    "width_um": tip_width,
                },
            },
            indent=2,
        )
        + "\n"
    )
