"""Primitive-only recreation of the two-guide smooth directional coupler."""

from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf


# Function-defining dimensions: keep these as simple top-level assignments so
# the conductor and JEE can inspect and substitute them deterministically.
total_length = 18.0
wg_width = 0.65
outer_spacing = 2.35
coupling_spacing = 0.96
approach_length = 8.0
coupling_length = 2.0
path_imbalance = 0.0
profile_samples_per_um = 24
layer = (1, 0)


# Normalized half-spacing samples measured from the supplied raster.  The
# transition is monotone and has zero slope at both ends; cubic Hermite
# interpolation retains the smooth S-bend silhouette while exposing the
# physical spacing and transition lengths above as live knobs.
PROFILE_X = (0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0)
PROFILE_Q = (1.0, 0.988, 0.941, 0.784, 0.553, 0.321, 0.157, 0.063, 0.0)


def _profile_value(u: float) -> float:
    """Cubic-Hermite interpolation of the normalized transition profile."""
    if u <= PROFILE_X[0]:
        return PROFILE_Q[0]
    if u >= PROFILE_X[-1]:
        return PROFILE_Q[-1]

    i = min(len(PROFILE_X) - 2, int(math.floor(u)))
    x0, x1 = PROFILE_X[i], PROFILE_X[i + 1]
    q0, q1 = PROFILE_Q[i], PROFILE_Q[i + 1]
    if i == 0:
        m0 = 0.0
    else:
        m0 = (PROFILE_Q[i + 1] - PROFILE_Q[i - 1]) / (PROFILE_X[i + 1] - PROFILE_X[i - 1])
    if i + 1 == len(PROFILE_X) - 1:
        m1 = 0.0
    else:
        m1 = (PROFILE_Q[i + 2] - PROFILE_Q[i]) / (PROFILE_X[i + 2] - PROFILE_X[i])

    t = (u - x0) / (x1 - x0)
    h00 = 2 * t**3 - 3 * t**2 + 1
    h10 = t**3 - 2 * t**2 + t
    h01 = -2 * t**3 + 3 * t**2
    h11 = t**3 - t**2
    return h00 * q0 + h10 * (x1 - x0) * m0 + h01 * q1 + h11 * (x1 - x0) * m1


def _half_spacing(x: float) -> float:
    """Return half the guide center spacing at longitudinal coordinate x."""
    transition = max(0.1, float(approach_length))
    flat = max(0.0, float(coupling_length))
    if x < transition:
        q = _profile_value(8.0 * x / transition)
    elif x <= transition + flat:
        q = 0.0
    else:
        mirror_x = total_length - x
        if mirror_x < transition:
            q = _profile_value(8.0 * mirror_x / transition)
        else:
            q = 0.0
    return 0.5 * coupling_spacing + 0.5 * (outer_spacing - coupling_spacing) * q


def _centerline_points(sign: float, extension: float = 0.0) -> list[tuple[float, float]]:
    """Sample one smooth guide centerline for gf.Path extrusion."""
    count = max(2, int(math.ceil(total_length * profile_samples_per_um)))
    points = []
    for index in range(count + 1):
        x = total_length * index / count
        points.append((x, sign * _half_spacing(x)))
    if extension > 0:
        points.append((total_length + extension, sign * _half_spacing(total_length)))
    return points


def _polyline_length(points: list[tuple[float, float]]) -> float:
    return sum(
        math.hypot(x1 - x0, y1 - y0)
        for (x0, y0), (x1, y1) in zip(points, points[1:])
    )


@gf.cell
def device() -> gf.Component:
    """Assemble the two extruded primitive waveguide paths."""
    component = gf.Component("smooth_directional_coupler")
    upper_points = _centerline_points(+1.0, path_imbalance)
    lower_points = _centerline_points(-1.0, 0.0)

    upper_path = gf.Path(upper_points)
    lower_path = gf.Path(lower_points)
    component << upper_path.extrude(width=wg_width, layer=layer)
    component << lower_path.extrude(width=wg_width, layer=layer)

    lengths = {
        "arms": {
            "upper": _polyline_length(upper_points),
            "lower": _polyline_length(lower_points),
        },
    }
    lengths["delta_length_um"] = abs(lengths["arms"]["upper"] - lengths["arms"]["lower"])
    lengths["coupler"] = {
        "length_um": total_length,
        "gap_um": coupling_spacing - wg_width,
        "width_um": wg_width,
    }
    (Path(__file__).parent / "lengths.json").write_text(json.dumps(lengths, indent=2))
    return component


if __name__ == "__main__":
    output = device()
    output.write_gds(Path(__file__).with_suffix(".gds"), with_metadata=False)
