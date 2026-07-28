from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


# Function-defining, JEE-substitutable tunables (all dimensions in um).
interaction_length = 99.9
transfer_length = 120.0
guide_width = 0.068
rail_gap = 0.033
rail_pitch = guide_width + rail_gap
center_rail_count = 5
bend_radius = 0.40
nested_offset = 2.65
outer_body_length = 105.5
outer_body_width = 0.472
vertical_width = 1.42
layer = (1, 0)
transfer_path = gf.Path(
    [(-transfer_length / 2, 0.0), (transfer_length / 2, 0.0)]
)


def add_rectangle(
    parent: gf.Component,
    *,
    length: float,
    width: float,
    x: float,
    y: float,
) -> None:
    """Place one axis-aligned rectangle primitive by its center."""
    ref = parent << gf.components.rectangle(size=(length, width), layer=layer)
    ref.move((-length / 2 + x, -width / 2 + y))


def add_vertical_rail(
    parent: gf.Component,
    *,
    x: float,
    y0: float,
    y1: float,
    width: float,
) -> None:
    """A vertical straight primitive, kept separate from horizontal rails."""
    height = abs(y1 - y0)
    add_rectangle(parent, length=width, width=height, x=x, y=(y0 + y1) / 2)


@gf.cell
def folded_distributed_coupler() -> gf.Component:
    c = gf.Component()

    # Five isolated transfer rails in the center.  The middle rail is an
    # extruded Path so transfer_length is directly measurable and perturbable.
    variable_rail = transfer_path.extrude(width=guide_width, layer=layer)
    c.add_ref(variable_rail)
    for index in range(center_rail_count):
        if index == center_rail_count // 2:
            continue
        y = (index - (center_rail_count - 1) / 2) * rail_pitch
        add_rectangle(
            c,
            length=interaction_length + 20.1,
            width=guide_width,
            x=0.0,
            y=y,
        )

    # Mirrored upper and lower folded bodies.  Each half contains a broad
    # return body, five narrow interaction rails, and four nested side returns.
    inner_rail_center = 0.800
    inner_side_y0 = inner_rail_center + bend_radius
    inner_side_y1 = 2.000
    outer_body_center = 0.502
    outer_side_y0 = 0.738
    outer_side_y1 = 2.000
    inner_side_x = interaction_length / 2 + nested_offset
    outer_side_x = outer_body_length / 2 + nested_offset / 2

    for sign in (-1.0, 1.0):
        add_rectangle(
            c,
            length=outer_body_length,
            width=outer_body_width,
            x=0.0,
            y=sign * outer_body_center,
        )

        for index in range(5):
            add_rectangle(
                c,
                length=interaction_length,
                width=guide_width,
                x=0.0,
                y=sign * (inner_rail_center + index * rail_pitch),
            )

        # The nested return edges are directionally widened in the source
        # drawing; separate rectangle primitives preserve that anisotropy.
        for offset_index in (0, 1):
            xoff = inner_side_x + offset_index * nested_offset
            add_vertical_rail(
                c,
                x=-xoff,
                y0=sign * inner_side_y0,
                y1=sign * inner_side_y1,
                width=vertical_width,
            )
            add_vertical_rail(
                c,
                x=xoff,
                y0=sign * inner_side_y0,
                y1=sign * inner_side_y1,
                width=vertical_width,
            )

        add_vertical_rail(
            c,
            x=-outer_side_x,
            y0=sign * outer_side_y0,
            y1=sign * outer_side_y1,
            width=vertical_width,
        )
        add_vertical_rail(
            c,
            x=outer_side_x,
            y0=sign * outer_side_y0,
            y1=sign * outer_side_y1,
            width=vertical_width,
        )

    return c


component = folded_distributed_coupler()
script_dir = Path(__file__).resolve().parent
component.write_gds(script_dir / "device.gds", with_metadata=False)

# The response contract is derived from the actual variable Path object.
variable_length = float(transfer_path.length())
(script_dir / "lengths.json").write_text(
    json.dumps(
        {
            "arms": {"reference": 0.0, "transfer": variable_length},
            "delta_length_um": variable_length,
        },
        indent=2,
    )
)
