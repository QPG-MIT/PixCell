from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

total_length_um = 18.0
footprint_height_um = 3.0
wg_width_um = 0.66
end_gap_um = 1.69
center_gap_um = 0.29
approach_length_um = 4.2
coupling_length_um = 6.0
end_straight_um = 1.8
smoothing_radius_um = 0.6
delta_length = 0.0


def guide_center_y(gap_um: float, *, upper: bool) -> float:
    half_pitch = 0.5 * (gap_um + wg_width_um)
    return 0.5 * footprint_height_um + (half_pitch if upper else -half_pitch)


def make_points(*, upper: bool, extra_length_um: float = 0.0) -> list[tuple[float, float]]:
    y_end = guide_center_y(end_gap_um, upper=upper)
    y_center = guide_center_y(center_gap_um, upper=upper)
    y_blend = 0.52 * y_end + 0.48 * y_center

    implied_total = 2.0 * end_straight_um + 2.0 * approach_length_um + coupling_length_um
    if abs(implied_total - total_length_um) > 1e-6:
        raise ValueError("Top-level length parameters must sum to total_length_um.")
    if end_straight_um <= 0 or approach_length_um <= 0:
        raise ValueError("Geometry is overconstrained: negative end straight length.")

    x0 = 0.0
    x1 = end_straight_um
    x2 = x1 + 0.48 * approach_length_um
    x3 = x1 + approach_length_um
    x4 = x3 + coupling_length_um + extra_length_um
    x5 = x4 + 0.52 * approach_length_um
    x6 = x4 + approach_length_um
    x7 = x6 + end_straight_um

    return [
        (x0, y_end),
        (x1, y_end),
        (x2, y_blend),
        (x3, y_center),
        (x4, y_center),
        (x5, y_blend),
        (x6, y_end),
        (x7, y_end),
    ]


def make_path(*, upper: bool, extra_length_um: float = 0.0) -> gf.Path:
    points = make_points(upper=upper, extra_length_um=extra_length_um)
    return gf.path.smooth(points, radius=smoothing_radius_um)


@gf.cell
def coupler() -> gf.Component:
    c = gf.Component("paper_swap_final4_coupler")

    upper_path = make_path(upper=True)
    lower_path = make_path(upper=False, extra_length_um=delta_length)

    upper_ref = c << upper_path.extrude(width=wg_width_um, layer=LAYER)
    lower_ref = c << lower_path.extrude(width=wg_width_um, layer=LAYER)

    c.add_port(
        "o1",
        center=(0.0, guide_center_y(end_gap_um, upper=True)),
        width=wg_width_um,
        orientation=180,
        layer=LAYER,
    )
    c.add_port(
        "o2",
        center=(0.0, guide_center_y(end_gap_um, upper=False)),
        width=wg_width_um,
        orientation=180,
        layer=LAYER,
    )
    c.add_port(
        "o3",
        center=(total_length_um, guide_center_y(end_gap_um, upper=True)),
        width=wg_width_um,
        orientation=0,
        layer=LAYER,
    )
    c.add_port(
        "o4",
        center=(total_length_um + delta_length, guide_center_y(end_gap_um, upper=False)),
        width=wg_width_um,
        orientation=0,
        layer=LAYER,
    )

    c.flatten()
    _ = upper_ref
    _ = lower_ref
    return c


def write_lengths(out_dir: Path, upper_path: gf.Path, lower_path: gf.Path) -> None:
    arms = {
        "upper": float(upper_path.length()),
        "lower": float(lower_path.length()),
    }
    payload = {
        "arms": arms,
        "delta_length_um": abs(arms["lower"] - arms["upper"]),
    }
    (out_dir / "lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    component = coupler()
    upper_path = make_path(upper=True)
    lower_path = make_path(upper=False, extra_length_um=delta_length)
    write_lengths(here, upper_path, lower_path)
    component.write_gds(here / "device.gds", with_metadata=False)
