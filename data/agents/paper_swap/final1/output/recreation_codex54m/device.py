import json
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")

import gdsfactory as gf
import numpy as np


LAYER = (1, 0)

device_length = 40.0
device_height = 1.7
center_y = 0.862

outer_start_x = 3.05
interaction_length = 23.15
branch_transition_length = 10.7
output_straight_length = device_length - outer_start_x - interaction_length - branch_transition_length

outer_start_offset_um = 0.269
outer_end_offset_um = 0.73

outer_tip_width = 0.056
outer_interaction_width = 0.224
output_width = 0.244

center_start_width = 0.272
center_end_width = 0.066
center_end_x = 25.15

branch_radius = 5.8

# Verification knob: adds real guide area and path length to the upper arm.
delta_length = 0.0


def xs(width: float) -> gf.CrossSection:
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def transition(width1: float, width2: float) -> gf.path.Transition:
    return gf.path.transition(xs(width1), xs(width2), width_type="linear")


def straight_path(length: float) -> gf.Path:
    return gf.path.straight(length=length)


def moved(component: gf.Component, x: float = 0.0, y: float = 0.0) -> gf.ComponentReference:
    ref = gf.Component().add_ref(component)
    ref.dmove((x, y))
    return ref


def outer_branch_path(sign: float, extra_length: float = 0.0) -> gf.Path:
    start_y = center_y + sign * outer_start_offset_um
    end_y = center_y + sign * outer_end_offset_um
    x0 = outer_start_x + interaction_length
    x1 = x0 + 2.0
    x2 = outer_start_x + interaction_length + branch_transition_length - 2.0
    x3 = device_length + extra_length
    points = np.array(
        [
            (x0, start_y),
            (x1, start_y),
            (x2, end_y),
            (x3, end_y),
        ]
    )
    return gf.path.smooth(points, radius=branch_radius)


@gf.cell
def build_device() -> gf.Component:
    assembly = gf.Component("phase_a_recreation")

    upper_start_y = center_y + outer_start_offset_um
    lower_start_y = center_y - outer_start_offset_um

    upper_taper = straight_path(interaction_length).extrude_transition(
        transition(outer_tip_width, outer_interaction_width)
    )
    upper_taper_ref = assembly << upper_taper
    upper_taper_ref.dmove((outer_start_x, upper_start_y))

    lower_taper = straight_path(interaction_length).extrude_transition(
        transition(outer_tip_width, outer_interaction_width)
    )
    lower_taper_ref = assembly << lower_taper
    lower_taper_ref.dmove((outer_start_x, lower_start_y))

    upper_branch = outer_branch_path(+1.0, extra_length=delta_length)
    upper_branch_comp = upper_branch.extrude_transition(
        transition(outer_interaction_width, output_width)
    )
    upper_branch_ref = assembly << upper_branch_comp

    lower_branch = outer_branch_path(-1.0, extra_length=0.0)
    lower_branch_comp = lower_branch.extrude_transition(
        transition(outer_interaction_width, output_width)
    )
    lower_branch_ref = assembly << lower_branch_comp

    center_path = straight_path(center_end_x)
    center_comp = center_path.extrude_transition(
        transition(center_start_width, center_end_width)
    )
    center_ref = assembly << center_comp
    center_ref.dmove((0.0, center_y))

    merged = gf.boolean(upper_taper_ref, lower_taper_ref, "or", layer=LAYER)
    merged = gf.boolean(merged, upper_branch_ref, "or", layer=LAYER)
    merged = gf.boolean(merged, lower_branch_ref, "or", layer=LAYER)
    merged = gf.boolean(merged, center_ref, "or", layer=LAYER)
    merged.info["lengths"] = {
        "upper": round(interaction_length + upper_branch.length(), 6),
        "lower": round(interaction_length + lower_branch.length(), 6),
    }
    return merged


if __name__ == "__main__":
    gf.clear_cache()
    component = build_device()
    workdir = Path(__file__).resolve().parent
    gds_path = workdir / "device.gds"
    component.write_gds(gds_path, with_metadata=False)

    lengths = component.info["lengths"]
    delta = abs(lengths["upper"] - lengths["lower"])
    (workdir / "lengths.json").write_text(
        json.dumps(
            {
                "arms": lengths,
                "delta_length_um": round(delta, 6),
            },
            indent=2,
        )
    )
