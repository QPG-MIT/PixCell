"""Primitive-only parametric recreation of the calibrated multi-rail device."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


layer = (1, 0)

# Function-defining, top-level parameters (all dimensions in um).
interaction_length = 120.0
rail_width = 0.066
rail_pitch = 0.1005
central_rail_count = 5
outer_rail_count = 5
slab_width = 0.470
slab_gap = 0.536
end_taper_length = 8.0
end_hook_x = 4.2
# Differential path extension is deliberately a real, measurable function knob.
delta_length = 0.0


def rail(length: float, width: float) -> gf.Component:
    """A straight rail made from a GDSFactory Path extrusion."""
    path = gf.Path()
    path.append(gf.path.straight(length=length))
    return path.extrude(width=width, layer=layer)


def curved_rail(points: list[tuple[float, float]]) -> gf.Component:
    """A smooth primitive path used for the observed rail end turns."""
    return gf.path.smooth(points, radius=0.35).extrude(width=rail_width, layer=layer)


@gf.cell
def multi_rail_device() -> gf.Component:
    c = gf.Component()
    mid_y = 2.0

    # Five central rails: one is the differential rail controlled by delta_length.
    for index in range(central_rail_count):
        length = interaction_length + (delta_length if index == 2 else 0.0)
        ref = c.add_ref(rail(length, rail_width))
        ref.movey(mid_y + (index - (central_rail_count - 1) / 2) * rail_pitch)

    # Symmetric broad loading slabs, separated from the central rail set.
    upper_slab = c.add_ref(gf.components.rectangle(size=(interaction_length - 2 * end_taper_length, slab_width), layer=layer))
    upper_slab.move((end_taper_length, mid_y - slab_gap / 2 - slab_width))
    lower_slab = c.add_ref(gf.components.rectangle(size=(interaction_length - 2 * end_taper_length, slab_width), layer=layer))
    lower_slab.move((end_taper_length, mid_y + slab_gap / 2))

    # Exterior repeated rails observed above and below the broad regions.
    outer_start = mid_y - slab_gap / 2 - slab_width - outer_rail_count * rail_pitch
    for index in range(outer_rail_count):
        top = c.add_ref(rail(interaction_length - 2 * end_taper_length, rail_width))
        top_y = outer_start + (index + 0.5) * rail_pitch - 0.012
        top.move((end_taper_length, top_y))
        bottom = c.add_ref(rail(interaction_length - 2 * end_taper_length, rail_width))
        bottom_y = 2 * mid_y - (outer_start + (index + 0.5) * rail_pitch) + 0.016
        bottom.move((end_taper_length, bottom_y))

        # Mirror-symmetric return turns at both longitudinal ends.
        top_end_y = 0.033 + index * rail_pitch
        bottom_end_y = 4.0 - top_end_y
        c.add_ref(curved_rail([(end_taper_length, top_y), (6.2, top_y), (5.2, top_end_y), (end_hook_x, top_end_y)]))
        c.add_ref(curved_rail([(interaction_length - end_taper_length, top_y), (113.8, top_y), (114.8, top_end_y), (interaction_length - end_hook_x, top_end_y)]))
        c.add_ref(curved_rail([(end_taper_length, bottom_y), (6.2, bottom_y), (5.2, bottom_end_y), (end_hook_x, bottom_end_y)]))
        c.add_ref(curved_rail([(interaction_length - end_taper_length, bottom_y), (113.8, bottom_y), (114.8, bottom_end_y), (interaction_length - end_hook_x, bottom_end_y)]))

    return c


if __name__ == "__main__":
    component = multi_rail_device()
    here = Path(__file__).resolve().parent
    component.write_gds(here / "device.gds", with_metadata=False)
    # The differential rail is a real Path extrusion; values are derived from it.
    (here / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {
                    "reference_um": interaction_length,
                    "differential_um": interaction_length + delta_length,
                },
                "delta_length_um": delta_length,
            },
            indent=2,
        )
    )
