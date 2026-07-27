"""Symmetric S-bend (raised-cosine) directional coupler, primitives-only."""

import gdsfactory as gf
import numpy as np

# ---- tunables (top-level, parametric contract) ----
wg_width_um = 0.664
gap_min_um = 0.309
gap_max_um = 1.705
coupling_length_um = 2.486
bend_length_um = 7.005
bus_length_um = 0.750
n_pts_per_segment = 120


def _sbend_offset(x_local, length, y0, y1):
    """Raised-cosine profile: zero slope at both ends, y0 -> y1 over [0, length]."""
    frac = (1 - np.cos(np.pi * x_local / length)) / 2.0
    return y0 + (y1 - y0) * frac


def _centerline(half_sep_max, half_sep_min):
    """Build the x, y arrays for one waveguide's half-separation centerline."""
    xs = []
    ys = []

    x0 = np.linspace(0, bus_length_um, n_pts_per_segment, endpoint=False)
    xs.append(x0)
    ys.append(np.full_like(x0, half_sep_max))

    x1 = np.linspace(0, bend_length_um, n_pts_per_segment, endpoint=False)
    xs.append(bus_length_um + x1)
    ys.append(_sbend_offset(x1, bend_length_um, half_sep_max, half_sep_min))

    x2 = np.linspace(0, coupling_length_um, n_pts_per_segment, endpoint=False)
    xs.append(bus_length_um + bend_length_um + x2)
    ys.append(np.full_like(x2, half_sep_min))

    x3 = np.linspace(0, bend_length_um, n_pts_per_segment, endpoint=False)
    xs.append(bus_length_um + bend_length_um + coupling_length_um + x3)
    ys.append(_sbend_offset(x3, bend_length_um, half_sep_min, half_sep_max))

    x4 = np.linspace(0, bus_length_um, n_pts_per_segment, endpoint=True)
    xs.append(bus_length_um + 2 * bend_length_um + coupling_length_um + x4)
    ys.append(np.full_like(x4, half_sep_max))

    return np.concatenate(xs), np.concatenate(ys)


@gf.cell
def sbend_coupler() -> gf.Component:
    c = gf.Component()

    half_sep_max = (gap_max_um + wg_width_um) / 2.0
    half_sep_min = (gap_min_um + wg_width_um) / 2.0

    xs, half_sep = _centerline(half_sep_max, half_sep_min)

    xsec = gf.cross_section.cross_section(width=wg_width_um, layer=(1, 0))

    top_points = np.column_stack([xs, half_sep])
    top_path = gf.Path(top_points)
    top_ref = c << gf.path.extrude(top_path, cross_section=xsec)

    bot_points = np.column_stack([xs, -half_sep])
    bot_path = gf.Path(bot_points)
    bot_ref = c << gf.path.extrude(bot_path, cross_section=xsec)

    c.add_port(name="o1", port=top_ref.ports["o1"])
    c.add_port(name="o2", port=top_ref.ports["o2"])
    c.add_port(name="o3", port=bot_ref.ports["o1"])
    c.add_port(name="o4", port=bot_ref.ports["o2"])

    return c


if __name__ == "__main__":
    import pathlib

    comp = sbend_coupler()
    comp.write_gds(str(pathlib.Path(__file__).parent / "device.gds"))
