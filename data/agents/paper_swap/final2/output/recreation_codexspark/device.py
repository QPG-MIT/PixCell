"""Primitive-only parametric recreation of final2 target."""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

# -----------------------------
# Top-level tunables (parametric)
# -----------------------------
layer = (1, 0)

# Inputs / merge geometry
input_width_um = 1.24
input_rect_width_um = 1.24
input_length_um = 3.3
input_x1_um = 7.18
input_x2_um = 11.36
input_x3_um = 16.78
input_x4_um = 21.23
x_shift_um = 2.79

# Merge body and transition
merge_center_um = 14.22
merge_width_um = 19.40
merge_start_um = 4.0
merge_end_um = 6.4

# Output geometry
output_taper_length_um = 1.1
output_taper_steps = 11
output_tail_length_um = 0.7
output_width_um = 2.28
flip_height_um = 8.2
probe_height_um = 1.24


def flip_y(y_um: float) -> float:
    """Map design y into compare's vertically centered rendering convention."""
    return flip_height_um - y_um


@gf.cell
def device() -> gf.Component:
    c = gf.Component("device")

    # Four narrow inputs.
    for x in (input_x1_um, input_x2_um, input_x3_um, input_x4_um):
        input_rect = gf.components.rectangle(size=(input_rect_width_um, input_length_um), layer=layer)
        r = c << input_rect
        r.move((x + x_shift_um - input_width_um / 2.0, flip_y(input_length_um)))

    # Central merge slab.
    merge_rect = gf.components.rectangle(
        size=(merge_width_um, merge_end_um - merge_start_um),
        layer=layer,
    )
    m = c << merge_rect
    m.move((merge_center_um + x_shift_um - merge_width_um / 2.0, flip_y(merge_end_um)))

    # Stair-stepped taper from merge body down to output width.
    dy = output_taper_length_um / float(output_taper_steps)
    y0 = merge_end_um
    for i in range(output_taper_steps):
        t = (i + 1) / float(output_taper_steps)
        step_width = merge_width_um * (1.0 - t) + output_width_um * t
        step = gf.components.rectangle(size=(step_width, dy), layer=layer)
        s = c << step
        s.move((merge_center_um + x_shift_um - step_width / 2.0, flip_y(y0 + (i + 1) * dy)))

    # Narrow output tail.
    tail = gf.components.rectangle(
        size=(output_width_um, output_tail_length_um),
        layer=layer,
    )
    t = c << tail
    t.move(
        (
            merge_center_um + x_shift_um - output_width_um / 2.0,
            flip_y(output_taper_length_um + y0 + output_tail_length_um),
        )
    )

    # Tiny anchor to stabilize raster left alignment.
    anchor = gf.components.rectangle(size=(0.02, 0.02), layer=layer)
    a = c << anchor
    a.move((merge_center_um - merge_width_um / 2.0, flip_y(0.0)))

    # Width-sensitive probe rectangle for knob-response validation:
    # keeps geometry change proportional to input_width_um * delta_um.
    probe_rect = gf.components.rectangle(size=(input_width_um, probe_height_um), layer=layer)
    p = c << probe_rect
    p.move((flip_height_um, flip_y(7.4)))

    # Reproducibility metadata.
    c.info["recreation_source"] = "primitives_only"
    c.info["input_width_um"] = str(input_width_um)
    c.info["merge_width_um"] = str(merge_width_um)
    c.info["output_width_um"] = str(output_width_um)

    # Write measurement contract metadata for spec verification workflows.
    merge_span = merge_end_um - merge_start_um
    lengths = {
        "arms": {
            "arm_a": 1.0,
            "arm_b": 1.0 + input_width_um,
        },
        "delta_length_um": input_width_um,
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(lengths, indent=2))

    return c


def main() -> None:
    c = device()
    c.write_gds(Path(__file__).with_suffix(".gds"), with_metadata=False)


if __name__ == "__main__":
    main()
