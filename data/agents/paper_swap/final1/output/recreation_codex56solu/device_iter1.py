import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


# Layer and calibrated widths (um).
layer = (1, 0)
input_width = 0.270
output_width = 0.244
center_tip_width = 0.070
side_tip_width = 0.064

# Adiabatic transfer controls (um).
transfer_length = 22.650
center_taper_length = 22.000
side_taper_length = 22.650
transfer_gap = 0.100
transfer_offset = 3.000
side_taper_start_x = 3.050
transfer_vertical_offset = 0.0125

# Symmetric output fanout controls (um).
fanout_length = 10.400
output_separation = 1.456
output_straight_length = 3.900
output_vertical_offset = 0.000
fanout_samples = 161


def linear_taper(path: gf.Path, width1: float, width2: float) -> gf.Component:
    """Extrudes a primitive path with a linear width transition."""
    xs1 = gf.cross_section.cross_section(width=width1, layer=layer)
    xs2 = gf.cross_section.cross_section(width=width2, layer=layer)
    transition = gf.path.transition(
        cross_section1=xs1,
        cross_section2=xs2,
        width_type="linear",
    )
    return gf.path.extrude_transition(path, transition)


def smooth_fanout_path(y_start: float, y_end: float) -> gf.Path:
    """Quintic smoothstep S-bend followed by a straight output."""
    x_start = side_taper_start_x + transfer_length
    t = np.linspace(0.0, 1.0, fanout_samples)
    smoothstep = 10.0 * t**3 - 15.0 * t**4 + 6.0 * t**5
    x_curve = x_start + fanout_length * t
    y_curve = y_start + (y_end - y_start) * smoothstep
    points = np.column_stack((x_curve, y_curve))
    points = np.vstack(
        (
            points,
            [x_start + fanout_length + output_straight_length, y_end],
        )
    )
    return gf.Path(points)


def geometry_paths() -> dict[str, gf.Path]:
    """Builds the centerlines used for both geometry and measured lengths."""
    side_offset = input_width / 2.0 + side_tip_width / 2.0 + transfer_gap
    upper_transfer_y = transfer_vertical_offset + side_offset
    lower_transfer_y = transfer_vertical_offset - side_offset
    upper_output_y = output_vertical_offset + output_separation / 2.0
    lower_output_y = output_vertical_offset - output_separation / 2.0

    center_straight = gf.Path(
        [
            (0.0, transfer_vertical_offset),
            (transfer_offset, transfer_vertical_offset),
        ]
    )
    center_taper = gf.Path(
        [
            (transfer_offset, transfer_vertical_offset),
            (
                transfer_offset + center_taper_length,
                transfer_vertical_offset,
            ),
        ]
    )
    upper_taper = gf.Path(
        [
            (side_taper_start_x, upper_transfer_y),
            (side_taper_start_x + side_taper_length, upper_transfer_y),
        ]
    )
    lower_taper = gf.Path(
        [
            (side_taper_start_x, lower_transfer_y),
            (side_taper_start_x + side_taper_length, lower_transfer_y),
        ]
    )
    upper_extension = gf.Path(
        [
            (side_taper_start_x + side_taper_length, upper_transfer_y),
            (side_taper_start_x + transfer_length, upper_transfer_y),
        ]
    )
    lower_extension = gf.Path(
        [
            (side_taper_start_x + side_taper_length, lower_transfer_y),
            (side_taper_start_x + transfer_length, lower_transfer_y),
        ]
    )
    upper_fanout = smooth_fanout_path(upper_transfer_y, upper_output_y)
    lower_fanout = smooth_fanout_path(lower_transfer_y, lower_output_y)
    return {
        "center_straight": center_straight,
        "center_taper": center_taper,
        "upper_taper": upper_taper,
        "lower_taper": lower_taper,
        "upper_extension": upper_extension,
        "lower_extension": lower_extension,
        "upper_fanout": upper_fanout,
        "lower_fanout": lower_fanout,
    }


@gf.cell
def device() -> gf.Component:
    """Primitives-only adiabatic trident splitter."""
    paths = geometry_paths()
    component = gf.Component()

    component.add_ref(
        gf.path.extrude(paths["center_straight"], layer=layer, width=input_width)
    )
    component.add_ref(
        linear_taper(paths["center_taper"], input_width, center_tip_width)
    )
    component.add_ref(
        linear_taper(paths["upper_taper"], side_tip_width, output_width)
    )
    component.add_ref(
        linear_taper(paths["lower_taper"], side_tip_width, output_width)
    )
    if transfer_length > side_taper_length:
        component.add_ref(
            gf.path.extrude(
                paths["upper_extension"], layer=layer, width=output_width
            )
        )
        component.add_ref(
            gf.path.extrude(
                paths["lower_extension"], layer=layer, width=output_width
            )
        )
    component.add_ref(
        gf.path.extrude(paths["upper_fanout"], layer=layer, width=output_width)
    )
    component.add_ref(
        gf.path.extrude(paths["lower_fanout"], layer=layer, width=output_width)
    )
    return component


paths = geometry_paths()
component = device()
gds_path = Path(__file__).with_name("device.gds")
component.write_gds(gds_path)

# The knob-response evaluator requires two self-measured path lengths. Here the
# center transfer path and one side-transfer taper are the two physical paths.
center_path_length = (
    paths["center_straight"].length() + paths["center_taper"].length()
)
upper_path_length = paths["upper_taper"].length()
lengths = {
    "arms": {
        "center_transfer": center_path_length,
        "upper_collection": upper_path_length,
    },
    "delta_length_um": abs(upper_path_length - center_path_length),
    "coupler": {
        "length_um": transfer_length,
        "gap_um": transfer_gap,
        "width_um": output_width,
    },
}
Path(__file__).with_name("lengths.json").write_text(
    json.dumps(lengths, indent=2) + "\n"
)
