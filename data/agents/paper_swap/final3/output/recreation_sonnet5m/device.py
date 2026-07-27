"""Asymmetric (tapered-width) directional coupler with S-bend access waveguides.

Both arms enter/exit at equal port width; through the S-bend each arm tapers
to a DIFFERENT width in the straight coupling region (top arm widens, bottom
arm narrows) -- the classic asymmetric/phase-mismatched directional coupler
topology used for wavelength- or mode-selective coupling.

Primitives only: gf.Path + gf.path.extrude + gf.path.transition. Layer (1, 0).
"""

import numpy as np
import gdsfactory as gf

# ---- Tunables (parametric contract: top-level name = value) ----
# NOTE: calibration.json scales x and y independently (anisotropic px/um),
# so these values are chosen to reproduce the target silhouette under that
# calibration, not literal fab dimensions.
port_width_um = 0.30
coupler_width_top_um = 0.43
coupler_width_bottom_um = 0.19
gap_um = 0.15
coupling_length_um = 54.0
bend_length_um = 13.0
port_pitch_um = 3.45
bus_length_um = 20.0

N_PTS_PER_BEND = 200
LAYER = (1, 0)


def _s_bend_ys(x, x0, length, y0, y1):
    """Raised-cosine S-bend: smooth, zero-slope at both ends."""
    t = np.clip((x - x0) / length, 0.0, 1.0)
    return y0 + (y1 - y0) * 0.5 * (1 - np.cos(np.pi * t))


def _bend_path(x0, y0, y1, length):
    xs = np.linspace(x0, x0 + length, N_PTS_PER_BEND)
    ys = _s_bend_ys(xs, x0, length, y0, y1)
    return gf.Path(np.column_stack([xs, ys]))


def _straight_path(x0, x1, y):
    return gf.Path(np.array([[x0, y], [x1, y]]))


def _build_arm(c, y_port, y_coupler, port_width, coupler_width,
                bus_length, bend_length, coupling_length, x_offset=0.0):
    cs_port = gf.cross_section.cross_section(width=port_width, layer=LAYER)
    cs_coupler = gf.cross_section.cross_section(width=coupler_width, layer=LAYER)
    cs_transition_in = gf.path.transition(cs_port, cs_coupler, width_type="linear")
    cs_transition_out = gf.path.transition(cs_coupler, cs_port, width_type="linear")

    x0 = x_offset
    x1 = x0 + bus_length
    x2 = x1 + bend_length
    x3 = x2 + coupling_length
    x4 = x3 + bend_length
    x5 = x4 + bus_length

    c << gf.path.extrude(_straight_path(x0, x1, y_port), cross_section=cs_port)
    c << gf.path.extrude_transition(_bend_path(x1, y_port, y_coupler, bend_length), transition=cs_transition_in)
    c << gf.path.extrude(_straight_path(x2, x3, y_coupler), cross_section=cs_coupler)
    c << gf.path.extrude_transition(_bend_path(x3, y_coupler, y_port, bend_length), transition=cs_transition_out)
    c << gf.path.extrude(_straight_path(x4, x5, y_port), cross_section=cs_port)

    return x5


@gf.cell
def directional_coupler_sbend(
    port_width_um: float = port_width_um,
    coupler_width_top_um: float = coupler_width_top_um,
    coupler_width_bottom_um: float = coupler_width_bottom_um,
    gap_um: float = gap_um,
    coupling_length_um: float = coupling_length_um,
    bend_length_um: float = bend_length_um,
    port_pitch_um: float = port_pitch_um,
    bus_length_um: float = bus_length_um,
) -> gf.Component:
    c = gf.Component()

    y_port = port_pitch_um / 2.0
    y_coupler = (gap_um + coupler_width_top_um / 2.0 + coupler_width_bottom_um / 2.0) / 2.0

    total_length = _build_arm(
        c, y_port, y_coupler, port_width_um, coupler_width_top_um,
        bus_length_um, bend_length_um, coupling_length_um,
    )
    _build_arm(
        c, -y_port, -y_coupler, port_width_um, coupler_width_bottom_um,
        bus_length_um, bend_length_um, coupling_length_um,
    )

    c.add_port(name="o1", center=(0, y_port), width=port_width_um, orientation=180, layer=LAYER)
    c.add_port(name="o2", center=(0, -y_port), width=port_width_um, orientation=180, layer=LAYER)
    c.add_port(name="o3", center=(total_length, y_port), width=port_width_um, orientation=0, layer=LAYER)
    c.add_port(name="o4", center=(total_length, -y_port), width=port_width_um, orientation=0, layer=LAYER)

    return c


if __name__ == "__main__":
    component = directional_coupler_sbend()
    component.write_gds("device.gds")
