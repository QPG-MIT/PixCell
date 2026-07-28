"""Parametric primitive recreation of the final4 two-arm directional coupler."""

from pathlib import Path

import gdsfactory as gf
import numpy as np
from scipy.interpolate import CubicSpline


# Geometry knobs (micrometres).  These assignments are intentionally live and
# are the interface used by the HOMI/JEE tooling.
footprint_length_um = 18.0
footprint_width_um = 3.0
wg_width_um = 0.66
min_gap_um = 0.30
coupling_length_um = 9.0
s_bend_rise_um = 0.70
delta_length = 0.0
path_sample_step_um = 0.04
layer = (1, 0)


# The measured half-device trajectory is a smooth, flat-ended S-bend.  Keeping
# the normalized shape separate from the dimensions makes the functional
# knobs above affect real geometry while preserving a compact parametric model.
_profile_u = np.array([0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1.0])
_profile_f = np.array([1.0, 0.991, 0.912, 0.705, 0.434, 0.207, 0.082, 0.014, 0.0])
_profile = CubicSpline(_profile_u, _profile_f, bc_type=((1, 0.0), (1, 0.0)))


def _centerline(sign: float) -> gf.Path:
    """Return one mirrored guide centerline as a sampled gf.Path."""

    mid_y = footprint_width_um / 2.0
    inner_half_separation = (wg_width_um + min_gap_um) / 2.0
    outer_half_separation = inner_half_separation + s_bend_rise_um
    half_span = coupling_length_um
    if half_span <= 0.0 or half_span > footprint_length_um / 2.0:
        raise ValueError("coupling_length_um must be in (0, footprint_length_um / 2]")

    # A zero-default path-length imbalance preserves the symmetric image.  A
    # positive value adds a horizontal upper-arm extension, so the measured
    # centerline length and physical area both respond to this function knob.
    extra_length = max(float(delta_length), 0.0) if sign > 0.0 else 0.0
    path_length_um = footprint_length_um + extra_length
    n = max(2, int(round(path_length_um / path_sample_step_um)) + 1)
    xs = np.linspace(0.0, path_length_um, n)
    us = np.minimum(xs, footprint_length_um - xs) / half_span
    us = np.clip(us, 0.0, 1.0)
    # sign=+1 is the upper arm and sign=-1 is its mirror image.
    half_separations = inner_half_separation + s_bend_rise_um * _profile(us)
    ys = mid_y + sign * half_separations
    return gf.Path(np.column_stack((xs, ys)))


@gf.cell
def directional_coupler() -> gf.Component:
    """Assemble the two extruded waveguide primitives."""

    component = gf.Component()
    upper_path = _centerline(+1.0)
    lower_path = _centerline(-1.0)
    upper = gf.path.extrude(upper_path, layer=layer, width=wg_width_um, simplify=0.001)
    lower = gf.path.extrude(lower_path, layer=layer, width=wg_width_um, simplify=0.001)
    component.add_ref(upper)
    component.add_ref(lower)

    # The physical arm lengths are derived from the actual centerline paths.
    lengths_path = Path(__file__).with_name("lengths.json")
    import json

    lengths_path.write_text(
        json.dumps(
            {
                "arms": {
                    "upper_um": float(upper_path.length()),
                    "lower_um": float(lower_path.length()),
                },
                "delta_length_um": float(upper_path.length() - lower_path.length()),
            },
            indent=2,
        )
        + "\n"
    )
    return component


if __name__ == "__main__":
    output_gds = Path(__file__).with_name("device.gds")
    directional_coupler().write_gds(output_gds, with_metadata=False)
