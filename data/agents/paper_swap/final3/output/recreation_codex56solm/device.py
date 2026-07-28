from pathlib import Path
import json

import gdsfactory as gf
import numpy as np


# Function-defining, JEE-substitutable geometry knobs (all dimensions in um).
guide_width_um = 0.30
top_interaction_width_start_um = 0.42
top_interaction_width_end_um = 0.30
bottom_interaction_width_start_um = 0.17
bottom_interaction_width_end_um = 0.29
top_entrance_bulge_width_um = 1.20
bottom_entrance_bulge_width_um = 0.70
top_output_bulge_width_um = 1.05
bottom_output_bulge_width_um = 1.00
coupling_gap_um = 0.17
transfer_length_um = 54.5
reference_transfer_length_um = 54.5
entrance_taper_length_um = 9.5
bend_length_um = 16.0
output_bend_length_um = 14.0
input_port_separation_um = 3.46
output_port_separation_um = 3.70
coupled_vertical_offset_um = -0.014
input_straight_um = 7.0
output_straight_um = 19.0
path_samples = 151
layer = (1, 0)


def _smoothstep(u: np.ndarray) -> np.ndarray:
    """Zero-slope interpolation for shallow adiabatic S-bends."""
    return 0.5 - 0.5 * np.cos(np.pi * u)


def _centerline(
    sign: float,
    interaction_length: float,
) -> tuple[gf.Path, tuple[float, ...]]:
    """Return one guide centerline and its cumulative section positions."""
    y_input = sign * input_port_separation_um / 2
    y_output = sign * output_port_separation_um / 2
    center_spacing = (
        top_interaction_width_start_um
        + bottom_interaction_width_start_um
    ) / 2 + coupling_gap_um
    y_coupled = sign * center_spacing / 2 + coupled_vertical_offset_um

    x0 = 0.0
    x1 = input_straight_um
    x2 = x1 + entrance_taper_length_um
    x3 = x2 + bend_length_um
    x4 = x3 + interaction_length
    x5 = x4 + output_bend_length_um
    x6 = x5 + output_straight_um

    xa = np.linspace(x0, x1, 8, endpoint=False)
    ya = np.full_like(xa, y_input)

    xb = np.linspace(x1, x2, 30, endpoint=False)
    yb = np.full_like(xb, y_input)

    u_in = np.linspace(0.0, 1.0, path_samples, endpoint=False)
    xc = x2 + bend_length_um * u_in
    yc = y_input + (y_coupled - y_input) * _smoothstep(u_in**1.2)

    xd = np.linspace(x3, x4, 80, endpoint=False)
    yd = np.full_like(xd, y_coupled)

    u_out = np.linspace(0.0, 1.0, path_samples, endpoint=False)
    xe = x4 + output_bend_length_um * u_out
    ye = y_coupled + (y_output - y_coupled) * _smoothstep(u_out)

    xf = np.linspace(x5, x6, 9)
    yf = np.full_like(xf, y_output)

    points = np.column_stack(
        [
            np.concatenate([xa, xb, xc, xd, xe, xf]),
            np.concatenate([ya, yb, yc, yd, ye, yf]),
        ]
    )
    path = gf.Path(points)

    width_markers = np.array([
        x1,
        x2,
        x2 + 0.20 * bend_length_um,
        x2 + 0.40 * bend_length_um,
        x2 + 0.50 * bend_length_um,
        x2 + 0.62 * bend_length_um,
        x2 + 0.80 * bend_length_um,
        x3,
        x4,
        x4 + 0.25 * output_bend_length_um,
        x4 + 0.45 * output_bend_length_um,
        x4 + 0.60 * output_bend_length_um,
        x4 + 0.78 * output_bend_length_um,
        x5,
        x6,
    ])
    nearest = [int(np.argmin(np.abs(points[:, 0] - x))) for x in width_markers]
    ds = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.concatenate([[0.0], np.cumsum(ds)])
    positions = tuple(float(cumulative[i] / cumulative[-1]) for i in nearest)
    return path, positions


def _variable_width_cross_section(
    positions: tuple[float, ...],
    interaction_start_width: float,
    interaction_end_width: float,
    entrance_bulge_width: float,
    output_bulge_width: float,
) -> gf.CrossSection:
    """Width profile: access -> entrance taper -> interaction taper -> access."""
    knots = np.array([0.0, *positions])
    entrance_shoulder = 0.35 * interaction_start_width + 0.65 * entrance_bulge_width
    entrance_low = 0.85 * interaction_start_width + 0.15 * entrance_bulge_width
    output_shoulder = 0.35 * guide_width_um + 0.65 * output_bulge_width
    widths = np.array([
        guide_width_um,
        guide_width_um,
        interaction_start_width,
        entrance_low,
        entrance_shoulder,
        entrance_bulge_width,
        entrance_bulge_width,
        entrance_low,
        interaction_start_width,
        interaction_end_width,
        0.55 * interaction_end_width + 0.45 * output_bulge_width,
        output_shoulder,
        output_bulge_width,
        0.70 * guide_width_um + 0.30 * output_bulge_width,
        guide_width_um,
        guide_width_um,
    ])

    def width_function(t: np.ndarray) -> np.ndarray:
        return np.interp(t, knots, widths)

    section = gf.Section(
        width=guide_width_um,
        width_function=width_function,
        layer=layer,
        port_names=("o1", "o2"),
    )
    return gf.CrossSection(sections=(section,))


@gf.cell
def asymmetric_adiabatic_coupler() -> gf.Component:
    component = gf.Component()

    top_path, top_positions = _centerline(+1.0, transfer_length_um)
    bottom_path, bottom_positions = _centerline(
        -1.0,
        reference_transfer_length_um,
    )

    top_xs = _variable_width_cross_section(
        top_positions,
        top_interaction_width_start_um,
        top_interaction_width_end_um,
        top_entrance_bulge_width_um,
        top_output_bulge_width_um,
    )
    bottom_xs = _variable_width_cross_section(
        bottom_positions,
        bottom_interaction_width_start_um,
        bottom_interaction_width_end_um,
        bottom_entrance_bulge_width_um,
        bottom_output_bulge_width_um,
    )

    component.add_ref(gf.path.extrude(top_path, cross_section=top_xs))
    component.add_ref(gf.path.extrude(bottom_path, cross_section=bottom_xs))
    return component


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    top_path, _ = _centerline(+1.0, transfer_length_um)
    bottom_path, _ = _centerline(-1.0, reference_transfer_length_um)
    top_length = float(top_path.length())
    bottom_length = float(bottom_path.length())

    lengths = {
        "arms": {
            "top_guide": top_length,
            "bottom_guide": bottom_length,
        },
        "delta_length_um": abs(top_length - bottom_length),
        "coupler": {
            "length_um": transfer_length_um,
            "gap_um": coupling_gap_um,
            "width_um": guide_width_um,
        },
    }
    (output_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    asymmetric_adiabatic_coupler().write_gds(
        output_dir / "device.gds",
        with_metadata=False,
    )
