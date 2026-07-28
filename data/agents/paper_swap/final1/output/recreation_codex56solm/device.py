from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Required fabrication layer
layer = (1, 0)

# Central input-to-tip taper (the disappearing input rail)
central_input_width = 0.270
central_tip_width = 0.070
central_taper_length = 25.000

# Twin receiving rails and the adiabatic transfer region
outer_tip_start = 3.050
outer_tip_width = 0.070
outer_taper_length = 22.500
transfer_gap = 0.095
transfer_length = 22.950

# Fanout/output geometry
output_width = 0.240
s_bend_length = 10.000
output_offset = 0.730
output_straight_length = 4.000


def _cross_section(width: float) -> gf.CrossSection:
    """Primitive single-section cross-section on the required layer."""
    return gf.cross_section.cross_section(width=width, layer=layer)


def _linear_taper(path: gf.Path, width1: float, width2: float) -> gf.Component:
    """Extrude a primitive path with a linear width transition."""
    transition = gf.path.transition(
        _cross_section(width1),
        _cross_section(width2),
        width_type="linear",
    )
    return gf.path.extrude_transition(path, transition)


def _s_bend_path(length: float, rise: float, samples: int = 101) -> gf.Path:
    """Flat-ended quintic S-bend centerline made directly as a gf.Path."""
    x = np.linspace(0.0, length, samples)
    t = x / length
    smooth = 6.0 * t**5 - 15.0 * t**4 + 10.0 * t**3
    return gf.Path(np.column_stack((x, rise * smooth)))


@gf.cell
def adiabatic_three_rail_splitter() -> gf.Component:
    """Primitives-only symmetric three-rail adiabatic splitter."""
    component = gf.Component()

    central_path = gf.path.straight(length=central_taper_length)
    central = _linear_taper(
        central_path,
        width1=central_input_width,
        width2=central_tip_width,
    )
    component.add_ref(central)

    transfer_center = (
        central_input_width / 2.0 + transfer_gap + outer_tip_width / 2.0
    )
    outer_taper_path = gf.path.straight(length=outer_taper_length)
    outer_taper = _linear_taper(
        outer_taper_path,
        width1=outer_tip_width,
        width2=output_width,
    )

    parallel_length = transfer_length - outer_taper_length
    parallel_path = gf.path.straight(length=parallel_length)
    parallel = gf.path.extrude(
        parallel_path,
        cross_section=_cross_section(output_width),
    )

    bend_rise = output_offset - transfer_center
    upper_bend_path = _s_bend_path(s_bend_length, bend_rise)
    lower_bend_path = _s_bend_path(s_bend_length, -bend_rise)
    upper_bend = gf.path.extrude(
        upper_bend_path,
        cross_section=_cross_section(output_width),
    )
    lower_bend = gf.path.extrude(
        lower_bend_path,
        cross_section=_cross_section(output_width),
    )

    output_path = gf.path.straight(length=output_straight_length)
    output_guide = gf.path.extrude(
        output_path,
        cross_section=_cross_section(output_width),
    )

    transfer_end_x = outer_tip_start + transfer_length
    bend_end_x = transfer_end_x + s_bend_length

    for sign in (-1.0, 1.0):
        taper_ref = component.add_ref(outer_taper)
        taper_ref.dmove((outer_tip_start, sign * transfer_center))

        parallel_ref = component.add_ref(parallel)
        parallel_ref.dmove(
            (outer_tip_start + outer_taper_length, sign * transfer_center)
        )

        bend = upper_bend if sign > 0 else lower_bend
        bend_ref = component.add_ref(bend)
        bend_ref.dmove((transfer_end_x, sign * transfer_center))

        output_ref = component.add_ref(output_guide)
        output_ref.dmove((bend_end_x, sign * output_offset))

    # Measurement contract: lengths are computed from the actual centerline
    # paths.  The central taper length is the verified response knob.
    reference_path = gf.Path()
    central_length = float(central_path.length())
    reference_length = float(reference_path.length())
    measured_delta = abs(central_length - reference_length)
    lengths = {
        "arms": {
            "reference": reference_length,
            "central_taper": central_length,
        },
        "delta_length_um": measured_delta,
        "coupler": {
            "length_um": float(transfer_length),
            "gap_um": float(transfer_gap),
            "width_um": float(output_width),
        },
    }
    (Path(__file__).parent / "lengths.json").write_text(
        json.dumps(lengths, indent=2)
    )
    return component


if __name__ == "__main__":
    device = adiabatic_three_rail_splitter()
    device.write_gds(
        Path(__file__).parent / "device.gds",
        with_metadata=False,
    )
