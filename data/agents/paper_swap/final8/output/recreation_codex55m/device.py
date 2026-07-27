from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Footprint and coordinate system.
footprint_length_um = 120.0
footprint_height_um = 4.0
origin_y_um = -footprint_height_um / 2

# Function-defining knobs.
interaction_length_um = 119.85
delta_length = 0.0
center_bar_width_um = 0.068
center_bar_pitch_um = 0.101
center_bar_count = 5
coupling_gap_um = 0.030
inner_tooth_width_um = 0.066
inner_tooth_pitch_um = 0.100
inner_tooth_count = 5
slab_height_um = 0.468
side_transition_length_um = 8.0
side_rail_width_um = 1.33
guide_width_um = center_bar_width_um
side_outer_top_edge_um = side_rail_width_um / 2
side_outer_bottom_edge_um = 4.0 - side_rail_width_um / 2

# Access/slab geometry.
center_start_x_um = 0.03
center_y_um = 0.0
upper_slab_center_y_um = 0.505
lower_slab_center_y_um = -0.505
inner_tooth_start_x_um = 8.15
inner_tooth_length_um = 103.6
outer_rail_x_left_um = 4.85
inner_rail_x_left_um = 7.20
inner_rail_x_right_um = 112.80
outer_rail_x_right_um = 115.15


def y_from_top(y_top_um: float) -> float:
    return footprint_height_um / 2 - y_top_um


def add_rect(
    c: gf.Component,
    *,
    x0: float,
    x1: float,
    y_top0: float,
    y_top1: float,
    name: str,
) -> None:
    width = max(x1 - x0, 0.001)
    height = max(y_top1 - y_top0, 0.001)
    ref = c << gf.components.rectangle(size=(width, height), layer=LAYER)
    ref.move((x0, y_from_top(y_top1)))
    ref.name = name


def add_path(c: gf.Component, points: list[tuple[float, float]], width: float, name: str) -> None:
    path = gf.Path(points)
    xs = gf.CrossSection(sections=(gf.Section(width=width, layer=LAYER),))
    ref = c << gf.path.extrude(path, xs)
    ref.name = name


@gf.cell
def recreate_device() -> gf.Component:
    c = gf.Component()

    # Full-length center grating bars.
    first_center_y_top = 1.772
    for i in range(center_bar_count):
        yc = first_center_y_top + i * center_bar_pitch_um
        add_rect(
            c,
            x0=center_start_x_um,
            x1=center_start_x_um + interaction_length_um + (delta_length if i == 0 else 0.0),
            y_top0=yc,
            y_top1=yc + center_bar_width_um,
            name=f"center_bar_{i}",
        )

    # Upper inner tooth stack and broad slab face.
    upper_tooth_first_top = 0.766
    for i in range(inner_tooth_count):
        yc = upper_tooth_first_top + i * inner_tooth_pitch_um
        add_rect(
            c,
            x0=inner_tooth_start_x_um,
            x1=inner_tooth_start_x_um + inner_tooth_length_um,
            y_top0=yc,
            y_top1=yc + inner_tooth_width_um,
            name=f"upper_tooth_{i}",
        )
    add_rect(
        c,
        x0=inner_tooth_start_x_um,
        x1=inner_tooth_start_x_um + inner_tooth_length_um,
        y_top0=1.265,
        y_top1=1.733,
        name="upper_slab_body",
    )

    # Lower mirror tooth stack and broad slab face.
    lower_slab_top = 2.269
    add_rect(
        c,
        x0=inner_tooth_start_x_um,
        x1=inner_tooth_start_x_um + inner_tooth_length_um,
        y_top0=lower_slab_top,
        y_top1=lower_slab_top + slab_height_um,
        name="lower_slab_body",
    )
    lower_tooth_first_top = 2.771
    for i in range(inner_tooth_count):
        yc = lower_tooth_first_top + i * inner_tooth_pitch_um
        add_rect(
            c,
            x0=inner_tooth_start_x_um,
            x1=inner_tooth_start_x_um + inner_tooth_length_um,
            y_top0=yc,
            y_top1=yc + inner_tooth_width_um,
            name=f"lower_tooth_{i}",
        )

    # Side access rails, approximated with smooth primitive paths.
    add_path(
        c,
        [
            (outer_rail_x_left_um, y_from_top(side_outer_top_edge_um)),
            (outer_rail_x_left_um + 0.25, y_from_top(0.45)),
            (outer_rail_x_left_um + 1.05, y_from_top(0.78)),
            (inner_rail_x_left_um, y_from_top(1.50)),
        ],
        side_rail_width_um,
        "upper_left_outer_rail",
    )
    add_path(
        c,
        [
            (inner_rail_x_left_um + 0.55, y_from_top(0.78)),
            (inner_rail_x_left_um + 0.20, y_from_top(1.10)),
            (inner_rail_x_left_um, y_from_top(1.50)),
        ],
        1.72,
        "upper_left_inner_flare",
    )
    add_path(
        c,
        [
            (outer_rail_x_right_um, y_from_top(side_outer_top_edge_um)),
            (outer_rail_x_right_um - 0.25, y_from_top(0.45)),
            (outer_rail_x_right_um - 1.05, y_from_top(0.78)),
            (inner_rail_x_right_um, y_from_top(1.50)),
        ],
        side_rail_width_um,
        "upper_right_outer_rail",
    )
    add_path(
        c,
        [
            (inner_rail_x_right_um - 0.55, y_from_top(0.78)),
            (inner_rail_x_right_um - 0.20, y_from_top(1.10)),
            (inner_rail_x_right_um, y_from_top(1.50)),
        ],
        1.72,
        "upper_right_inner_flare",
    )

    add_path(
        c,
        [
            (outer_rail_x_left_um, y_from_top(side_outer_bottom_edge_um)),
            (outer_rail_x_left_um + 0.25, y_from_top(3.55)),
            (outer_rail_x_left_um + 1.05, y_from_top(3.22)),
            (inner_rail_x_left_um, y_from_top(2.50)),
        ],
        side_rail_width_um,
        "lower_left_outer_rail",
    )
    add_path(
        c,
        [
            (inner_rail_x_left_um + 0.55, y_from_top(3.22)),
            (inner_rail_x_left_um + 0.20, y_from_top(2.90)),
            (inner_rail_x_left_um, y_from_top(2.50)),
        ],
        1.72,
        "lower_left_inner_flare",
    )
    add_path(
        c,
        [
            (outer_rail_x_right_um, y_from_top(side_outer_bottom_edge_um)),
            (outer_rail_x_right_um - 0.25, y_from_top(3.55)),
            (outer_rail_x_right_um - 1.05, y_from_top(3.22)),
            (inner_rail_x_right_um, y_from_top(2.50)),
        ],
        side_rail_width_um,
        "lower_right_outer_rail",
    )
    add_path(
        c,
        [
            (inner_rail_x_right_um - 0.55, y_from_top(3.22)),
            (inner_rail_x_right_um - 0.20, y_from_top(2.90)),
            (inner_rail_x_right_um, y_from_top(2.50)),
        ],
        1.72,
        "lower_right_inner_flare",
    )

    return c


if __name__ == "__main__":
    component = recreate_device()
    out_dir = Path(__file__).resolve().parent
    writable = component.copy()
    writable.flatten()
    writable.write_gds(out_dir / "device.gds", with_metadata=False)
    lengths = {
        "arms": {
            "reference_center_bar": interaction_length_um,
            "coupled_center_bar": interaction_length_um + delta_length,
        },
        "delta_length_um": delta_length,
    }
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
