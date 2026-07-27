from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


layer = (1, 0)
footprint_length_um = 120.0
footprint_width_um = 4.0

# Main geometric knob requested by the phase instructions.
delta_length = 0.0

# Primary waveguide geometry.
wg_width_um = 0.070
bend_radius_um = 0.190

# Layout spans and repeated bundle spacing.
bundle_span_um = footprint_length_um - wg_width_um
top_open_y_um = footprint_width_um - wg_width_um / 2
bottom_open_y_um = wg_width_um / 2
bar_width_um = 0.070
bar_span_um = footprint_length_um - bar_width_um

# Top and bottom bundles are built as nested U-shapes with staggered return
# heights, matching the visible stacked lobes in the reference image.
top_turn_ys_um = (3.23, 3.14, 3.04, 2.94, 2.84, 2.74)
bottom_turn_ys_um = (0.77, 0.86, 0.96, 1.05, 1.14, 1.23)
center_bar_ys_um = (2.20, 2.11, 2.02, 1.93, 1.84)
top_body_center_um = 2.51
top_body_height_um = 0.48
bottom_body_center_um = 1.49
bottom_body_height_um = 0.48
body_inset_um = 11.2


def _u_path(
    *,
    x_left_um: float,
    x_right_um: float,
    y_open_um: float,
    y_turn_um: float,
) -> gf.Path:
    """Rounded U-shaped path centered on the requested strip."""
    points = np.array(
        [
            [x_left_um, y_open_um],
            [x_left_um, y_turn_um],
            [x_right_um, y_turn_um],
            [x_right_um, y_open_um],
        ],
        dtype=float,
    )
    return gf.path.smooth(points, radius=bend_radius_um)


def _add_path(component: gf.Component, path: gf.Path, *, width_um: float) -> None:
    """Extrude one path on the requested layer and add it to the component."""
    ref = component << path.extrude(layer=layer, width=width_um)
    ref.move((0, 0))


@gf.cell
def build_device() -> gf.Component:
    c = gf.Component("paper_swap_final8_recreation")

    x_left_um = wg_width_um / 2
    x_right_um = footprint_length_um - wg_width_um / 2
    x_left_bar_um = bar_width_um / 2
    x_right_bar_um = footprint_length_um - bar_width_um / 2

    # Upper arm, used for the measured delta_length contract.
    upper_arm = _u_path(
        x_left_um=x_left_um,
        x_right_um=x_right_um + delta_length,
        y_open_um=top_open_y_um,
        y_turn_um=3.06,
    )
    _add_path(c, upper_arm, width_um=wg_width_um)

    # Lower arm, mirrored counterpart without the extra delta.
    lower_arm = _u_path(
        x_left_um=x_left_um,
        x_right_um=x_right_um,
        y_open_um=bottom_open_y_um,
        y_turn_um=0.94,
    )
    _add_path(c, lower_arm, width_um=wg_width_um)

    # Repeated top bundle.
    for y_turn_um in top_turn_ys_um:
        _add_path(
            c,
            _u_path(
                x_left_um=x_left_um,
                x_right_um=x_right_um,
                y_open_um=top_open_y_um,
                y_turn_um=y_turn_um,
            ),
            width_um=wg_width_um,
        )

    # Repeated bottom bundle.
    for y_turn_um in bottom_turn_ys_um:
        _add_path(
            c,
            _u_path(
                x_left_um=x_left_um,
                x_right_um=x_right_um,
                y_open_um=bottom_open_y_um,
                y_turn_um=y_turn_um,
            ),
            width_um=wg_width_um,
        )

    # Central horizontal bar stack.
    for y_um in center_bar_ys_um:
        bar_path = gf.path.straight(bar_span_um)
        ref = c << bar_path.extrude(layer=layer, width=bar_width_um)
        ref.move((x_left_bar_um, y_um))

    # Filled body blocks that anchor the large top and bottom lobes.
    body_span_um = footprint_length_um - 2 * body_inset_um

    top_body_path = gf.path.straight(body_span_um)
    top_body_ref = c << top_body_path.extrude(layer=layer, width=top_body_height_um)
    top_body_ref.move((body_inset_um, top_body_center_um))

    bottom_body_path = gf.path.straight(body_span_um)
    bottom_body_ref = c << bottom_body_path.extrude(layer=layer, width=bottom_body_height_um)
    bottom_body_ref.move((body_inset_um, bottom_body_center_um))

    lengths = {
        "arms": {
            "upper_arm_um": float(upper_arm.length()),
            "lower_arm_um": float(lower_arm.length()),
        },
        "delta_length_um": float(abs(upper_arm.length() - lower_arm.length())),
    }
    (Path(__file__).with_name("lengths.json")).write_text(json.dumps(lengths, indent=2))
    return c


def main() -> None:
    component = build_device().copy()
    component.flatten()
    component.write_gds(Path(__file__).with_suffix(".gds"))


if __name__ == "__main__":
    main()
