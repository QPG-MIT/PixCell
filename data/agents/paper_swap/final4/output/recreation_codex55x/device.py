import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


length_um = 18.0
wg_width_um = 0.652
min_gap_um = 0.3149
port_gap_um = 1.6837
interaction_length_um = 0.0
input_straight_um = 1.1032
curve_power = 1.6532
num_points: int = 801
delta_length = 0.0

layer = (1, 0)
gds_filename = "device.gds"


def _smoothstep_separation(x: np.ndarray) -> np.ndarray:
    """Mirror-symmetric raised-cosine separation between the two centerlines."""
    center_sep_min = wg_width_um + min_gap_um
    center_sep_port = wg_width_um + port_gap_um

    transition_length = (length_um - 2 * input_straight_um - interaction_length_um) / 2
    if transition_length <= 0:
        raise ValueError("transition_length must remain positive")

    x_edge = np.minimum(x, length_um - x)
    u = np.clip((x_edge - input_straight_um) / transition_length, 0.0, 1.0)
    raised_cosine = 0.5 * (1.0 + np.cos(np.pi * u))
    profile = np.where(x_edge <= input_straight_um, 1.0, raised_cosine**curve_power)

    if interaction_length_um > 0:
        left_end = input_straight_um + transition_length
        right_start = length_um - input_straight_um - transition_length
        profile = np.where((x >= left_end) & (x <= right_start), 0.0, profile)

    return center_sep_min + (center_sep_port - center_sep_min) * profile


def _make_paths() -> tuple[gf.Path, gf.Path]:
    x = np.linspace(0.0, length_um, num_points)
    separation = _smoothstep_separation(x)
    top_points = np.column_stack((x, 1.5 + separation / 2))
    bottom_points = np.column_stack((x, 1.5 - separation / 2))

    if delta_length > 0:
        top_points = np.vstack((top_points, [length_um + delta_length, top_points[-1, 1]]))
    elif delta_length < 0:
        bottom_points = np.vstack((bottom_points, [length_um - delta_length, bottom_points[-1, 1]]))

    return gf.Path(top_points), gf.Path(bottom_points)


@gf.cell
def coupler_recreation() -> gf.Component:
    component = gf.Component()
    top_path, bottom_path = _make_paths()

    top = gf.path.extrude(top_path, width=wg_width_um, layer=layer, simplify=1e-4)
    bottom = gf.path.extrude(bottom_path, width=wg_width_um, layer=layer, simplify=1e-4)
    component << top
    component << bottom
    component.flatten()

    return component


def write_lengths(paths: tuple[gf.Path, gf.Path]) -> None:
    top_path, bottom_path = paths
    arms = {
        "top": float(top_path.length()),
        "bottom": float(bottom_path.length()),
    }
    payload = {
        "arms": arms,
        "delta_length_um": abs(arms["top"] - arms["bottom"]),
    }
    Path("lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    gf.clear_cache()
    paths = _make_paths()
    component = coupler_recreation()
    component.write_gds(gds_filename, with_metadata=False)
    write_lengths(paths)
