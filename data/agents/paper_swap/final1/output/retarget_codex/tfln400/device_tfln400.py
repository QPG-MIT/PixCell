from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Stack/spec constants.
wavelength_um = 1.55
footprint_length_um = 150.0
footprint_width_um = 20.0
wg_width_um = 1.2
min_feature_um = 0.5

# Function-defining mode-evolution knobs.
input_center_y_um = 0.0
input_straight_length_um = 1.0
taper_segment_1_length_um = 25.0
taper_segment_2_length_um = 99.0
taper_segment_3_length_um = 25.0
center_width_0_um = 1.2
center_width_1_um = 0.95
center_width_2_um = 0.75
center_width_3_um = 0.5
side_width_0_um = 0.5
side_width_1_um = 0.75
side_width_2_um = 0.95
side_width_3_um = 1.2
coupled_gap_um = 0.5
upper_coupled_y_um = 1.35
lower_coupled_y_um = -1.35
upper_output_y_um = 1.35
lower_output_y_um = -1.35
output_separation_um = 2.7

# Output extension knobs. Baseline is zero so the 150 um budget is used by
# transfer; perturbing upper/lower lengths still changes real geometry.
s_bend_length_um = 0.0
upper_output_straight_length_um = 0.0
lower_output_straight_length_um = 0.0
s_bend_points = 128


def smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def taper_segments() -> list[tuple[float, float, float]]:
    return [
        (taper_segment_1_length_um, center_width_0_um, center_width_1_um),
        (taper_segment_2_length_um, center_width_1_um, center_width_2_um),
        (taper_segment_3_length_um, center_width_2_um, center_width_3_um),
    ]


def side_taper_segments() -> list[tuple[float, float, float]]:
    return [
        (taper_segment_1_length_um, side_width_0_um, side_width_1_um),
        (taper_segment_2_length_um, side_width_1_um, side_width_2_um),
        (taper_segment_3_length_um, side_width_2_um, side_width_3_um),
    ]


def make_s_bend_path(
    x0: float,
    y0: float,
    y1: float,
    bend_length: float,
    straight_length: float,
    npoints: int,
) -> gf.Path:
    if bend_length <= 0.0 or abs(y1 - y0) < 1e-9:
        return gf.Path([(x0, y0), (x0 + bend_length + straight_length, y1)])
    points: list[tuple[float, float]] = []
    for i in range(npoints):
        t = i / (npoints - 1)
        points.append((x0 + bend_length * t, y0 + (y1 - y0) * smoothstep(t)))
    points.append((x0 + bend_length + straight_length, y1))
    return gf.Path(points)


def add_taper_chain(
    c: gf.Component,
    y: float,
    segments: list[tuple[float, float, float]],
    x_start: float,
) -> float:
    x = x_start
    for length, width1, width2 in segments:
        taper = gf.components.taper(
            length=length,
            width1=width1,
            width2=width2,
            layer=LAYER,
            with_bbox=False,
        )
        ref = c << taper
        ref.dmove((x, y))
        x += length
    return x


@gf.cell
def recreate_device() -> gf.Component:
    c = gf.Component()

    c << gf.path.extrude(
        gf.Path([(0.0, input_center_y_um), (input_straight_length_um, input_center_y_um)]),
        width=wg_width_um,
        layer=LAYER,
    )

    x_out = add_taper_chain(c, input_center_y_um, taper_segments(), input_straight_length_um)
    for y in (upper_coupled_y_um, lower_coupled_y_um):
        add_taper_chain(c, y, side_taper_segments(), input_straight_length_um)

    if s_bend_length_um > 0.0 or upper_output_straight_length_um > 0.0:
        upper_path = make_s_bend_path(
            x_out,
            upper_coupled_y_um,
            upper_output_y_um,
            s_bend_length_um,
            upper_output_straight_length_um,
            s_bend_points,
        )
        c << gf.path.extrude(upper_path, width=wg_width_um, layer=LAYER)
    if s_bend_length_um > 0.0 or lower_output_straight_length_um > 0.0:
        lower_path = make_s_bend_path(
            x_out,
            lower_coupled_y_um,
            lower_output_y_um,
            s_bend_length_um,
            lower_output_straight_length_um,
            s_bend_points,
        )
        c << gf.path.extrude(lower_path, width=wg_width_um, layer=LAYER)

    c.add_port(
        "in",
        center=(0.0, input_center_y_um),
        width=wg_width_um,
        orientation=180,
        layer=LAYER,
    )
    c.add_port(
        "out_top",
        center=(footprint_length_um, upper_output_y_um),
        width=wg_width_um,
        orientation=0,
        layer=LAYER,
    )
    c.add_port(
        "out_bot",
        center=(footprint_length_um, lower_output_y_um),
        width=wg_width_um,
        orientation=0,
        layer=LAYER,
    )
    return c


def write_lengths(script_dir: Path) -> None:
    upper = upper_output_straight_length_um
    lower = lower_output_straight_length_um
    payload = {
        "arms": {
            "upper_output_straight": upper,
            "lower_output_straight": lower,
        },
        "delta_length_um": abs(upper - lower),
    }
    (script_dir / "lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    component = recreate_device()
    flat_component = component.copy()
    flat_component.flatten()
    flat_component.write_gds(out_dir / "device_tfln400.gds", with_metadata=False)
    write_lengths(out_dir)
