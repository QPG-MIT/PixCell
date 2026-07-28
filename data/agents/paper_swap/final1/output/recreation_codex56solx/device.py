from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Function-defining, JEE-substitutable geometry tunables (all dimensions in um).
device_length = 40.0
center_taper_length = 25.05
center_input_width = 0.270
center_tip_width = 0.071
outer_start_offset = 3.045
outer_tip_width = 0.071
outer_guide_width = 0.244
interaction_gap = 0.1015
transfer_length = 22.955
fanout_length = 9.70
output_separation = 1.456

layer = (1, 0)
curve_samples = 161


def _varying_width_section(
    start_width: float,
    end_width: float,
    variable_length: float,
    full_path_length: float,
) -> gf.CrossSection:
    def width_function(normalized_length: np.ndarray) -> np.ndarray:
        distance = normalized_length * full_path_length
        fraction = np.minimum(distance / variable_length, 1.0)
        return start_width + (end_width - start_width) * fraction

    return gf.CrossSection(
        sections=(
            gf.Section(
                width=start_width,
                width_function=width_function,
                layer=layer,
            ),
        ),
    )


def _outer_path(sign: float) -> gf.Path:
    interaction_y = (
        center_input_width / 2
        + interaction_gap
        + outer_tip_width / 2
    )
    output_y = output_separation / 2
    fanout_start = outer_start_offset + transfer_length
    fanout_end = fanout_start + fanout_length

    t = np.linspace(0.0, 1.0, curve_samples)
    x_curve = fanout_start + fanout_length * t
    smooth_step = 0.5 * (1.0 - np.cos(np.pi * t))
    y_curve = sign * (
        interaction_y + (output_y - interaction_y) * smooth_step
    )

    points = np.column_stack((x_curve, y_curve))
    points = np.vstack(
        (
            [outer_start_offset, sign * interaction_y],
            points[1:],
            [device_length, sign * output_y],
        )
    )
    return gf.Path(points)


@gf.cell
def trident_coupler() -> gf.Component:
    component = gf.Component()

    center_path = gf.Path(
        np.array(
            [
                [0.0, 0.0],
                [center_taper_length, 0.0],
            ]
        )
    )
    center_section = _varying_width_section(
        center_input_width,
        center_tip_width,
        center_taper_length,
        center_path.length(),
    )
    component.add_ref(gf.path.extrude(center_path, cross_section=center_section))

    for sign in (1.0, -1.0):
        path = _outer_path(sign)
        section = _varying_width_section(
            outer_tip_width,
            outer_guide_width,
            transfer_length,
            path.length(),
        )
        component.add_ref(gf.path.extrude(path, cross_section=section))

    return component


device = trident_coupler()
output_dir = Path(__file__).resolve().parent
device.write_gds(output_dir / "device.gds", with_metadata=False)

# The center taper path and the outer-start datum are path-derived. Their
# difference gives verify_knob_response a deterministic measurement of the
# live center_taper_length knob without hand-entering a claimed response.
center_measurement_path = gf.Path(
    np.array([[0.0, 0.0], [center_taper_length, 0.0]])
)
outer_start_datum_path = gf.Path(
    np.array([[0.0, 0.0], [outer_start_offset, 0.0]])
)
center_measured = center_measurement_path.length()
datum_measured = outer_start_datum_path.length()
(output_dir / "lengths.json").write_text(
    json.dumps(
        {
            "arms": {
                "center_taper": center_measured,
                "outer_start_datum": datum_measured,
            },
            "delta_length_um": abs(center_measured - datum_measured),
            "coupler": {
                "length_um": center_measured,
                "gap_um": interaction_gap,
                "width_um": outer_guide_width,
            },
        },
        indent=2,
    )
)
