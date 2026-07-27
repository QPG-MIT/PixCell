from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Stack/spec constants.
wavelength_um = 1.55
footprint_length_um = 150.0
footprint_width_um = 18.0
wg_width_um = 1.0
min_feature_um = 0.4

# Function-defining mode-evolution knobs.
input_center_y_um = 0.0
input_straight_length_um = 1.0
coupled_taper_length_um = 149.0
center_tip_width_um = 0.4
side_tip_width_um = 0.4
coupled_gap_um = 0.4
upper_coupled_y_um = 1.1
lower_coupled_y_um = -1.1
upper_output_y_um = 1.1
lower_output_y_um = -1.1
output_separation_um = 2.2

# Output extension knobs. Baseline is zero to spend the device budget on transfer;
# the top-level knobs still move real geometry for the response check.
s_bend_length_um = 0.0
upper_output_straight_length_um = 0.0
lower_output_straight_length_um = 0.0
s_bend_points = 128


def smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


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


@gf.cell
def recreate_device() -> gf.Component:
    c = gf.Component()

    c << gf.path.extrude(
        gf.Path([(0.0, input_center_y_um), (input_straight_length_um, input_center_y_um)]),
        width=wg_width_um,
        layer=LAYER,
    )

    center_taper = gf.components.taper(
        length=coupled_taper_length_um,
        width1=wg_width_um,
        width2=center_tip_width_um,
        layer=LAYER,
        with_bbox=False,
    )
    center_ref = c << center_taper
    center_ref.dmove((input_straight_length_um, input_center_y_um))

    for y in (upper_coupled_y_um, lower_coupled_y_um):
        side_taper = gf.components.taper(
            length=coupled_taper_length_um,
            width1=side_tip_width_um,
            width2=wg_width_um,
            layer=LAYER,
            with_bbox=False,
        )
        side_ref = c << side_taper
        side_ref.dmove((input_straight_length_um, y))

    x_out = input_straight_length_um + coupled_taper_length_um
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
    flat_component.write_gds(out_dir / "device_sin400.gds", with_metadata=False)
    write_lengths(out_dir)
