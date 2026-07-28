"""Primitive-only recreation of the paired S-bend directional coupler."""

from pathlib import Path

import gdsfactory as gf
import numpy as np

layer = (1, 0)
wg_width = 0.30
upper_wg_width = 0.34
lower_wg_width = 0.27
port_separation = 3.475
coupler_gap = 0.16
coupling_length = 52.6
reference_coupling_length = 52.585
left_s_bend_length = 17.0
right_s_bend_length = 17.4
access_length = 16.5
upper_left_port_y = 3.754
lower_left_port_y = 0.300
upper_right_port_y = 3.828
lower_right_port_y = 0.168
upper_coupler_y = 2.235
lower_coupler_y = 1.771


def s_bend_points(
    x0: float, y0: float, dx: float, dy: float, profile: str, n: int = 121
) -> np.ndarray:
    """Image-calibrated, zero-slope S-bend centerline represented as a GF Path."""
    profile_t = np.array([0.00, 0.08, 0.15, 0.23, 0.31, 0.39, 0.46, 0.53, 0.61, 0.69, 0.77, 0.85, 0.92, 1.00])
    if profile == "lower_left":
        profile_y = np.array([0.00, 0.01, 0.02, 0.05, 0.09, 0.17, 0.28, 0.48, 0.75, 0.85, 0.92, 0.97, 0.99, 1.00])
    elif profile == "right":
        profile_y = np.array([0.00, 0.02, 0.05, 0.10, 0.18, 0.34, 0.55, 0.68, 0.80, 0.88, 0.93, 0.97, 0.99, 1.00])
    else:
        profile_y = np.array([0.00, 0.01, 0.03, 0.06, 0.12, 0.30, 0.43, 0.53, 0.65, 0.86, 0.92, 0.97, 0.99, 1.00])
    t = np.linspace(0.0, 1.0, n)
    return np.column_stack((x0 + dx * t, y0 + dy * np.interp(t, profile_t, profile_y)))


@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component()
    x1 = access_length
    x2 = x1 + left_s_bend_length
    paths = {}
    for name, left_y, central_y, right_y, width, interaction_length, left_profile in (
        ("lower", lower_left_port_y, lower_coupler_y, lower_right_port_y, lower_wg_width, reference_coupling_length, "lower_left"),
        ("upper", upper_left_port_y, upper_coupler_y, upper_right_port_y, upper_wg_width, coupling_length, "upper_left"),
    ):
        x3 = x2 + interaction_length
        x4 = x3 + right_s_bend_length
        points = np.vstack(
            (
                np.array([[0.0, left_y], [x1, left_y]]),
                s_bend_points(x1, left_y, left_s_bend_length, central_y - left_y, left_profile)[1:],
                np.array([[x3, central_y]]),
                s_bend_points(x3, central_y, right_s_bend_length, right_y - central_y, "right")[1:],
                np.array([[x4 + access_length, right_y]]),
            )
        )
        path = gf.Path(points)
        paths[name] = path
        c.add_ref(path.extrude(width=width, layer=layer))
    upper_length = float(paths["upper"].length())
    lower_length = float(paths["lower"].length())
    Path(__file__).with_name("lengths.json").write_text(
        __import__("json").dumps(
            {
                "arms": {"upper": upper_length, "lower": lower_length},
                "delta_length_um": abs(upper_length - lower_length),
            },
            indent=2,
        )
    )
    return c


if __name__ == "__main__":
    component = directional_coupler().copy()
    component.flatten()
    component.write_gds(Path(__file__).with_name("device.gds"))
