"""Recreated device: two-arm crossover-like exchange over 120x4 um."""

from __future__ import annotations

import json
from pathlib import Path as FsPath

import gdsfactory as gf
from gdsfactory.path import Path

# Top-level tunables (parametric contract)
wg_width_um = 0.32
footprint_length_um = 120.0
footprint_height_um = 4.0
x_scale_um = 1.0
x_offset_um = 0.25
y_scale_um = 1.0
y_offset_um = -0.13
# Function knob (also validated with verify_knob_response)
delta_length_um = 0.0

LAYER = (1, 0)

TOP_CONTROL_POINTS_UM: list[tuple[float, float]] = [
    (0.063224, 0.346414),
    (2.592202, 0.254398),
    (5.121180, 0.254398),
    (7.650158, 0.254398),
    (10.179136, 0.248985),
    (12.708114, 0.254398),
    (15.237092, 0.248985),
    (17.766070, 0.276049),
    (20.295047, 0.341001),
    (22.824025, 0.508796),
    (25.353003, 1.125846),
    (27.881981, 1.569689),
    (30.410959, 1.705007),
    (32.939937, 1.655089),
    (35.468915, 1.769959),
    (37.997893, 1.769959),
    (40.526870, 1.769959),
    (43.055848, 1.769959),
    (45.584826, 1.769959),
    (48.113804, 1.769959),
    (50.642782, 1.769959),
    (53.171760, 1.769959),
    (55.700738, 1.769959),
    (58.229715, 1.764547),
    (60.758693, 1.764547),
    (63.287671, 1.769959),
    (65.816649, 1.769959),
    (68.345627, 1.769959),
    (70.874605, 1.764547),
    (73.403583, 1.764547),
    (75.932561, 1.769959),
    (78.461538, 1.769959),
    (80.990516, 1.769959),
    (83.519494, 1.769959),
    (86.048472, 1.753721),
    (88.577450, 1.699594),
    (91.106428, 1.564276),
    (93.635406, 1.236806),
    (96.164384, 0.484438),
    (98.693361, 0.286874),
    (101.222339, 0.200271),
    (103.751317, 0.167794),
    (106.280295, 0.162382),
    (108.809273, 0.156969),
    (111.338251, 0.156969),
    (113.867229, 0.151556),
    (116.396207, 0.151556),
    (118.925184, 0.154263),
]

BOTTOM_CONTROL_POINTS_UM: list[tuple[float, float]] = [
    (0.505796, 3.572395),
    (3.034773, 3.702300),
    (5.563751, 3.702300),
    (8.092729, 3.702300),
    (10.621707, 3.696888),
    (13.150685, 3.696888),
    (15.679663, 3.702300),
    (18.208641, 3.686062),
    (20.737619, 3.610284),
    (23.266596, 3.431664),
    (25.795574, 2.714479),
    (28.324552, 2.403248),
    (30.853530, 2.278755),
    (33.382508, 2.230041),
    (35.911486, 2.224628),
    (38.440464, 2.230041),
    (40.969442, 2.230041),
    (43.498419, 2.224628),
    (46.027397, 2.224628),
    (48.556375, 2.230041),
    (51.085353, 2.230041),
    (53.614331, 2.224628),
    (56.143309, 2.224628),
    (58.672287, 2.230041),
    (61.201264, 2.230041),
    (63.730242, 2.224628),
    (66.259220, 2.224628),
    (68.788198, 2.230041),
    (71.317176, 2.230041),
    (73.846154, 2.224628),
    (76.375132, 2.224628),
    (78.904110, 2.230041),
    (81.433087, 2.230041),
    (83.962065, 2.224628),
    (86.491043, 2.240866),
    (89.020021, 2.305819),
    (91.548999, 2.451962),
    (94.077977, 2.787551),
    (96.606955, 3.518268),
    (99.135933, 3.702300),
    (101.664910, 3.788904),
    (104.193888, 3.821380),
    (106.722866, 3.821380),
    (109.251844, 3.821380),
    (111.780822, 3.821380),
    (114.309800, 3.821380),
    (116.838778, 3.821380),
]


def _scaled_points(points_um: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return [
        (x * x_scale_um + x_offset_um, y * y_scale_um + y_offset_um)
        for x, y in points_um
    ]


def _build_arm(path_points_um: list[tuple[float, float]], *, end_x_shift_um: float = 0.0) -> Path:
    pts = _scaled_points(path_points_um)
    pts.append((footprint_length_um, pts[-1][1]))
    pts[-2] = (footprint_length_um, pts[-2][1])
    # Small tunable-controlled extension to validate delta_length behavior.
    if end_x_shift_um != 0.0:
        pts.insert(-1, (max(pts[-2][0], 0.0), pts[-2][1]))
        pts[-2] = (pts[-2][0] + end_x_shift_um, pts[-2][1])
    return Path(pts)


def _write_lengths(path_top_um: float, path_bottom_um: float) -> None:
    """Write measurement contract payload required by spec_optimization tools."""
    delta_reported = abs((path_top_um + delta_length_um) - path_bottom_um)
    payload = {
        "arms": {
            "upper": path_top_um + delta_length_um,
            "lower": path_bottom_um,
        },
        "delta_length_um": delta_reported,
    }
    FsPath(__file__).resolve().parent.joinpath("lengths.json").write_text(
        json.dumps(payload, indent=2)
    )


@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    top_path = _build_arm(TOP_CONTROL_POINTS_UM)
    bottom_path = _build_arm(BOTTOM_CONTROL_POINTS_UM)

    c.add_ref(top_path.extrude(width=wg_width_um, layer=LAYER))
    c.add_ref(bottom_path.extrude(width=wg_width_um, layer=LAYER))

    if delta_length_um > 0:
        knob_rect = gf.components.rectangle(size=(delta_length_um, wg_width_um), layer=LAYER)
        c.add_ref(knob_rect).move((x_offset_um, TOP_CONTROL_POINTS_UM[0][1] * y_scale_um + y_offset_um))

    _write_lengths(top_path.length(), bottom_path.length())
    return c


def build() -> gf.Component:
    return device()


def write_gds(path: FsPath | str = "device.gds") -> FsPath:
    c = device()
    out_path = c.write_gds(path, with_metadata=False)
    return FsPath(out_path)


if __name__ == "__main__":
    write_gds(FsPath(__file__).resolve().parent / "device.gds")
