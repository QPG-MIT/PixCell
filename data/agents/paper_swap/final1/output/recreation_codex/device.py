from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


LAYER = (1, 0)

# Footprint and main guide dimensions.
footprint_length_um = 40.0
footprint_width_um = 1.7
rail_width_um = 0.244

# Central input guide: short full-width section followed by an adiabatic taper.
input_center_y_um = 0.016
input_flat_length_um = 3.10
input_length_um = 25.10
input_width_left_um = 0.270
input_width_right_um = 0.076

# Coupled side rails.
rail_taper_start_um = 3.10
rail_taper_length_um = 23.00
rail_tip_width_um = 0.070
upper_coupled_y_um = 0.282
lower_coupled_y_um = -0.260

# Output fanout.  Upper/lower straight lengths are independent so the required
# knob-response check can perturb one real guide length without dummy geometry.
s_bend_length_um = 9.30
upper_output_straight_length_um = 4.60
lower_output_straight_length_um = 4.60
output_separation_um = 1.458
s_bend_points = 96


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
    points: list[tuple[float, float]] = []
    for i in range(npoints):
        t = i / (npoints - 1)
        x = x0 + bend_length * t
        y = y0 + (y1 - y0) * smoothstep(t)
        points.append((x, y))
    points.append((x0 + bend_length + straight_length, y1))
    return gf.Path(points)


@gf.cell
def recreate_device() -> gf.Component:
    c = gf.Component()

    flat = gf.path.extrude(
        gf.Path([(0.0, input_center_y_um), (input_flat_length_um, input_center_y_um)]),
        width=input_width_left_um,
        layer=LAYER,
    )
    c << flat

    input_taper = gf.components.taper(
        length=input_length_um - input_flat_length_um,
        width1=input_width_left_um,
        width2=input_width_right_um,
        layer=LAYER,
        with_bbox=False,
    )
    input_ref = c << input_taper
    input_ref.dmove((input_flat_length_um, input_center_y_um))

    for y in (upper_coupled_y_um, lower_coupled_y_um):
        rail_taper = gf.components.taper(
            length=rail_taper_length_um,
            width1=rail_tip_width_um,
            width2=rail_width_um,
            layer=LAYER,
            with_bbox=False,
        )
        rail_ref = c << rail_taper
        rail_ref.dmove((rail_taper_start_um, y))

    x_fanout = rail_taper_start_um + rail_taper_length_um
    upper_output_y = output_separation_um / 2.0
    lower_output_y = -output_separation_um / 2.0

    upper_path = make_s_bend_path(
        x_fanout,
        upper_coupled_y_um,
        upper_output_y,
        s_bend_length_um,
        upper_output_straight_length_um,
        s_bend_points,
    )
    lower_path = make_s_bend_path(
        x_fanout,
        lower_coupled_y_um,
        lower_output_y,
        s_bend_length_um,
        lower_output_straight_length_um,
        s_bend_points,
    )

    c << gf.path.extrude(upper_path, width=rail_width_um, layer=LAYER)
    c << gf.path.extrude(lower_path, width=rail_width_um, layer=LAYER)

    c.add_port(
        "in",
        center=(0.0, input_center_y_um),
        width=input_width_left_um,
        orientation=180,
        layer=LAYER,
    )
    c.add_port(
        "out_top",
        center=(footprint_length_um, upper_output_y),
        width=rail_width_um,
        orientation=0,
        layer=LAYER,
    )
    c.add_port(
        "out_bot",
        center=(footprint_length_um, lower_output_y),
        width=rail_width_um,
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
    flat_component.write_gds(out_dir / "device.gds", with_metadata=False)
    write_lengths(out_dir)
