"""Primitives-only parametric reconstruction of the supplied directional coupler."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Function-defining dimensions in microns.  Keep these as simple top-level
# assignments so HOMI/JEE and the independent evaluator can perturb them.
wg_width = 0.65
tip_width = 0.65
taper_length = 0.02
input_gap = 1.70
coupling_gap = 0.30
s_bend_length = 8.23
transfer_length = 1.50
delta_length = 0.0

layer = (1, 0)
s_bend_samples = 301


def _cubic_bezier_points(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
) -> list[tuple[float, float]]:
    """Return a centerline for one zero-slope cubic S-bend."""
    t = np.linspace(0.0, 1.0, s_bend_samples)
    omt = 1.0 - t
    x = omt**3 * p0[0] + 3 * omt**2 * t * p1[0] + 3 * omt * t**2 * p2[0] + t**3 * p3[0]
    y = omt**3 * p0[1] + 3 * omt**2 * t * p1[1] + 3 * omt * t**2 * p2[1] + t**3 * p3[1]
    return list(zip(x.tolist(), y.tolist(), strict=True))


def _rail_points(
    port_y: float,
    coupling_y: float,
    phase_extension: float = 0.0,
) -> list[tuple[float, float]]:
    """Build one rail from its two S-bends and its straight interaction section."""
    x0 = taper_length
    x1 = x0 + s_bend_length
    x2 = x1 + transfer_length
    x3 = x2 + s_bend_length

    left = _cubic_bezier_points(
        (x0, port_y),
        (x0 + s_bend_length / 2, port_y),
        (x0 + s_bend_length / 2, coupling_y),
        (x1, coupling_y),
    )
    right = _cubic_bezier_points(
        (x2, coupling_y),
        (x2 + s_bend_length / 2, coupling_y),
        (x2 + s_bend_length / 2, port_y),
        (x3, port_y),
    )
    points = left + [(x2, coupling_y)] + right[1:]
    if phase_extension:
        points.append((x3 + phase_extension, port_y))
    return points


@gf.cell
def directional_coupler() -> gf.Component:
    """Two primitive path extrusions with a close parallel transfer section."""
    component = gf.Component()

    total_height = 2 * wg_width + input_gap
    lower_port_y = wg_width / 2
    upper_port_y = total_height - wg_width / 2
    lower_coupling_y = total_height / 2 - (wg_width + coupling_gap) / 2
    upper_coupling_y = total_height / 2 + (wg_width + coupling_gap) / 2

    lower_path = gf.Path(_rail_points(lower_port_y, lower_coupling_y))
    upper_path = gf.Path(
        _rail_points(upper_port_y, upper_coupling_y, phase_extension=delta_length)
    )
    component.add_ref(lower_path.extrude(width=wg_width, layer=layer))
    component.add_ref(upper_path.extrude(width=wg_width, layer=layer))

    base_right_taper_x = 2 * taper_length + 2 * s_bend_length + transfer_length - taper_length
    for y in (lower_port_y, upper_port_y):
        left_taper = component.add_ref(
            gf.components.taper(
                length=taper_length,
                width1=tip_width,
                width2=wg_width,
                layer=layer,
                with_bbox=False,
            )
        )
        left_taper.dmovey(y)

        right_taper = component.add_ref(
            gf.components.taper(
                length=taper_length,
                width1=wg_width,
                width2=tip_width,
                layer=layer,
                with_bbox=False,
            )
        )
        if y == upper_port_y:
            right_taper.dmove((0.0, 0.0), (base_right_taper_x + delta_length, y))
        else:
            right_taper.dmove((0.0, 0.0), (base_right_taper_x, y))

    # These are measured from the actual gf.Path objects used above.  The
    # two baseline rails are equal; delta_length is a genuine one-rail phase
    # trim that adds centerline material and moves its output lead.
    component.info["lower_arm_length_um"] = float(lower_path.length() + 2 * taper_length)
    component.info["upper_arm_length_um"] = float(upper_path.length() + 2 * taper_length)
    return component


workdir = Path(__file__).resolve().parent
device = directional_coupler()

lower_arm_length = float(device.info["lower_arm_length_um"])
upper_arm_length = float(device.info["upper_arm_length_um"])
(workdir / "lengths.json").write_text(
    json.dumps(
        {
            "arms": {"lower": lower_arm_length, "upper": upper_arm_length},
            "delta_length_um": abs(upper_arm_length - lower_arm_length),
        },
        indent=2,
    )
)
device.write_gds(workdir / "device.gds", with_metadata=False)
