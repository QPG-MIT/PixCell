"""Parametric primitive-only recreation of the supplied four-port crossing."""

from __future__ import annotations

import json
import math
from pathlib import Path

import gdsfactory as gf


# Image-matched, top-level geometric tunables (all units are um).
port_width_um = 0.23
access_lead_length_um = 0.55
delta_length = 0.0
taper_length_um = 1.80
peak_width_um = 0.91
center_width_um = 0.38
profile_exponent = 1.05
taper_segments = 16
layer = (1, 0)


@gf.cell
def east_horn() -> gf.Component:
    """One center-to-east crossing arm, made only of taper/straight primitives."""
    component = gf.Component()
    x = 0.0

    # Smooth almond profile: a narrow center grows to a multimode maximum,
    # then contracts to the single-mode access guide.
    widths = []
    for index in range(taper_segments + 1):
        fraction = index / taper_segments
        baseline = center_width_um * (1.0 - fraction) + port_width_um * fraction
        excess = peak_width_um - (center_width_um + port_width_um) / 2.0
        widths.append(round((baseline + excess * math.sin(math.pi * fraction) ** profile_exponent) / 0.002) * 0.002)

    segment_length = taper_length_um / taper_segments
    for width1, width2 in zip(widths[:-1], widths[1:]):
        segment = component.add_ref(
            gf.components.taper(
                length=segment_length,
                width1=width1,
                width2=width2,
                layer=layer,
                with_bbox=False,
            )
        )
        segment.dmove((x, 0.0))
        x += segment_length

    lead = component.add_ref(
        gf.components.straight(
            length=access_lead_length_um + delta_length,
            cross_section=gf.cross_section.strip(width=port_width_um, layer=layer),
        )
    )
    lead.dmove((x, 0.0))
    return component


@gf.cell
def fixed_horn() -> gf.Component:
    """A symmetric arm whose access lead is held fixed for the knob audit."""
    component = gf.Component()
    x = 0.0

    widths = []
    for index in range(taper_segments + 1):
        fraction = index / taper_segments
        baseline = center_width_um * (1.0 - fraction) + port_width_um * fraction
        excess = peak_width_um - (center_width_um + port_width_um) / 2.0
        widths.append(round((baseline + excess * math.sin(math.pi * fraction) ** profile_exponent) / 0.002) * 0.002)

    segment_length = taper_length_um / taper_segments
    for width1, width2 in zip(widths[:-1], widths[1:]):
        segment = component.add_ref(
            gf.components.taper(
                length=segment_length,
                width1=width1,
                width2=width2,
                layer=layer,
                with_bbox=False,
            )
        )
        segment.dmove((x, 0.0))
        x += segment_length

    lead = component.add_ref(
        gf.components.straight(
            length=access_lead_length_um,
            cross_section=gf.cross_section.strip(width=port_width_um, layer=layer),
        )
    )
    lead.dmove((x, 0.0))
    return component


@gf.cell
def four_port_crossing() -> gf.Component:
    """Four identical optical transitions joined at their narrow inner ends."""
    component = gf.Component()
    center = taper_length_um + access_lead_length_um

    east = component.add_ref(east_horn())
    east.dmove((center, center))

    for angle in (90, 180, 270):
        arm = component.add_ref(fixed_horn())
        arm.drotate(angle)
        arm.dmove((center, center))

    return component


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    component = four_port_crossing()
    # These values are derived directly from the straight centerline lengths.
    centerline_length_um = taper_length_um + access_lead_length_um
    (output_dir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {
                    "east": centerline_length_um + delta_length,
                    "west": centerline_length_um,
                },
                "delta_length_um": delta_length,
            },
            indent=2,
        )
        + "\n"
    )
    component.write_gds(output_dir / "device.gds", with_metadata=False)
