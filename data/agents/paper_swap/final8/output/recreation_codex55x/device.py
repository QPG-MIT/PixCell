from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Footprint and primary function knobs.
footprint_length_um = 120.0
footprint_width_um = 4.0
transfer_length_um = 120.0
rail_width_um = 0.066
rail_pitch_um = 0.100
center_gap_um = 0.100

# Upper/lower access and side-return knobs.
access_slab_height_um = 0.468
access_slab_length_um = 104.2
side_rail_width_um = 1.46
inner_side_rail_width_um = 1.42
side_taper_length_um = 3.9
side_gap_um = 0.82
comb_tip_width_um = rail_width_um

# Evaluator verifier knob. At the target value it is zero; perturbing it
# lengthens one real rail by rail_width_um * delta area.
trim_delta_length_um = 0.0


def _add_rect(c: gf.Component, x0: float, x1: float, y0: float, y1: float) -> None:
    """Add an axis-aligned rectangle using the primitive rectangle component."""
    if x1 <= x0 or y1 <= y0:
        return
    rect = gf.components.rectangle(size=(x1 - x0, y1 - y0), layer=LAYER)
    ref = c << rect
    ref.move((x0, y0))


def _add_hrail(c: gf.Component, x0: float, x1: float, y: float, width: float) -> None:
    _add_rect(c, x0, x1, y - width / 2, y + width / 2)


def _add_path(c: gf.Component, points: list[tuple[float, float]], width: float) -> None:
    path = gf.Path(points)
    section = gf.path.extrude(path, width=width, layer=LAYER)
    c << section


def _mirror_x(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return [(footprint_length_um - x, y) for x, y in points]


def _mirror_y(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    return [(x, -y) for x, y in points]


def _add_side_returns(c: gf.Component) -> None:
    outer_left = [
        (4.94, 2.00),
        (5.08, 1.88),
        (5.30, 1.75),
        (5.48, 1.65),
        (5.66, 1.55),
        (5.88, 1.45),
        (6.12, 1.35),
        (6.37, 1.25),
        (6.63, 1.15),
        (7.18, 0.95),
        (8.26, 0.75),
    ]
    inner_left = [
        (7.18, 2.00),
        (7.34, 1.85),
        (7.51, 1.75),
        (7.69, 1.65),
        (7.88, 1.55),
        (8.11, 1.45),
        (8.40, 1.35),
        (8.82, 1.25),
        (8.94, 1.15),
    ]

    for pts, width in (
        (outer_left, side_rail_width_um),
        (_mirror_x(outer_left), side_rail_width_um),
        (inner_left, inner_side_rail_width_um),
        (_mirror_x(inner_left), inner_side_rail_width_um),
    ):
        _add_path(c, pts, width)
        _add_path(c, _mirror_y(pts), width)


def _add_access_slabs(c: gf.Component) -> None:
    # Stacked rectangles follow the measured curved taper envelope without raw polygons.
    upper_slices = [
        (0.267, 0.350, 9.77, 110.14),
        (0.350, 0.450, 8.73, 111.19),
        (0.450, 0.550, 8.09, 111.82),
        (0.550, 0.650, 7.63, 112.31),
        (0.650, 0.735, 7.19, 112.69),
    ]
    for y0, y1, x0, x1 in upper_slices:
        _add_rect(c, x0, x1, y0, y1)
        _add_rect(c, x0, x1, -y1, -y0)


def _add_comb_rails(c: gf.Component) -> None:
    upper_runs = [
        (1.2015, [(5.689, 7.310), (7.860, 112.024), (112.603, 114.253)]),
        (1.1015, [(5.920, 7.628), (8.121, 111.764), (112.285, 113.993)]),
        (1.0015, [(6.152, 7.976), (8.410, 111.445), (111.908, 113.761)]),
        (0.9015, [(6.413, 8.439), (8.815, 111.040), (111.445, 113.501)]),
        (0.8015, [(6.702, 9.076), (9.481, 110.403), (110.808, 113.211)]),
    ]
    for y, runs in upper_runs:
        for x0, x1 in runs:
            _add_hrail(c, x0, x1, y, comb_tip_width_um)
            _add_hrail(c, x0, x1, -y, comb_tip_width_um)


def _add_center_rails(c: gf.Component) -> None:
    y_centers = [0.194, 0.095, -0.007, -0.107, -0.208]
    for index, y in enumerate(y_centers):
        extra = trim_delta_length_um if index == 2 else 0.0
        _add_hrail(c, 0.0, transfer_length_um + extra, y, rail_width_um)


@gf.cell
def recreated_device() -> gf.Component:
    c = gf.Component()
    _add_side_returns(c)
    _add_access_slabs(c)
    _add_comb_rails(c)
    _add_center_rails(c)
    return c


def _write_lengths() -> None:
    arms = {
        "reference_center_rail": transfer_length_um,
        "trimmed_center_rail": transfer_length_um + trim_delta_length_um,
    }
    payload = {
        "arms": arms,
        "delta_length_um": abs(arms["trimmed_center_rail"] - arms["reference_center_rail"]),
    }
    Path(__file__).with_name("lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    gf.clear_cache()
    component = recreated_device()
    component.write_gds(Path(__file__).with_name("device.gds"), with_metadata=False)
    _write_lengths()
