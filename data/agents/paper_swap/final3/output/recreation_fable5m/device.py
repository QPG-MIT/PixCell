"""Symmetric directional coupler — primitives-only parametric recreation.

Two waveguides run from separated ports through smooth (tanh) S-bends into a
long parallel coupling section with a sub-wavelength gap, then S-bend back
apart. Each guide is a chain of short gf.Path straight-segment extrusions
whose width follows the local slope (the source figure is drawn with a
constant stroke in a 11.7x vertically exaggerated space, so the real-space
stripe thickens in the bends). gdsfactory 9.20.7, layer (1, 0).
"""

import math

import gdsfactory as gf

# ---- function-defining tunables (um) ----
total_length_um = 120.0
wg_width_um = 0.29            # guide width at the ports (real space)
coupling_gap_um = 0.18        # edge-to-edge gap in the coupling section
coupling_length_um = 68.9     # transfer length (distance between S-bend centers)
sbend_scale_um = 3.1          # tanh scale of the S-bends (adiabaticity)
port_pitch_left_um = 3.447    # port center-to-center separation, left side
port_pitch_right_um = 3.664   # port center-to-center separation, right side

# drawing-fidelity tunables (match the source figure, not device function)
gap_center_offset_um = -0.040   # coupling-pair midline offset from device axis
w_top_coupling_um = 0.36        # top guide width in the coupling section
w_bot_coupling_um = 0.22        # bottom guide width in the coupling section
center_x_um = 59.75             # x of the coupling-section midpoint
render_anisotropy_top = 11.68    # bend-thickening factor, top guide (drawn fatter)
render_anisotropy_bot = 11.68    # bend-thickening factor, bottom guide (drawn thinner)
seg_um = 0.4                    # sampling step for the segment chain

LAYER = (1, 0)


def _envelope(x: float, xc_l: float, xc_r: float, a: float) -> float:
    """0 at the ports, 1 in the coupling section."""
    return 0.25 * (1.0 + math.tanh((x - xc_l) / a)) * (1.0 - math.tanh((x - xc_r) / a))


@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component()
    xc_l = center_x_um - coupling_length_um / 2.0
    xc_r = center_x_um + coupling_length_um / 2.0
    c_top = gap_center_offset_um + coupling_gap_um / 2.0 + w_top_coupling_um / 2.0
    c_bot = gap_center_offset_um - coupling_gap_um / 2.0 - w_bot_coupling_um / 2.0

    guides = [
        (port_pitch_left_um / 2.0, port_pitch_right_um / 2.0, c_top, w_top_coupling_um, render_anisotropy_top),
        (-port_pitch_left_um / 2.0, -port_pitch_right_um / 2.0, c_bot, w_bot_coupling_um, render_anisotropy_bot),
    ]

    n = max(2, int(round(total_length_um / seg_um)))
    dx = total_length_um / n

    for p_l, p_r, c_mid, w_coup, aniso in guides:
        def y_of(x: float) -> float:
            s = _envelope(x, xc_l, xc_r, sbend_scale_um)
            port_level = p_l + (p_r - p_l) * x / total_length_um
            return port_level * (1.0 - s) + c_mid * s

        def w_of(x: float, y0: float, y1: float) -> float:
            s = _envelope(x, xc_l, xc_r, sbend_scale_um)
            base = wg_width_um + (w_coup - wg_width_um) * s
            slope = (y1 - y0) / dx
            w = base * math.sqrt(1.0 + (aniso * slope) ** 2)
            return round(w * 500.0) / 500.0  # snap to 2 dbu (kfactory port rule)

        xs = [i * dx for i in range(n + 1)]
        ys = [y_of(x) for x in xs]
        arm_length = 0.0
        for i in range(n):
            w = w_of((xs[i] + xs[i + 1]) / 2.0, ys[i], ys[i + 1])
            seg = gf.Path([(xs[i], ys[i]), (xs[i + 1], ys[i + 1])])
            arm_length += seg.length()
            c << gf.path.extrude(seg, layer=LAYER, width=w)
        arm_lengths.append(arm_length)
    return c


arm_lengths: list[float] = []

if __name__ == "__main__":
    import json
    from pathlib import Path as _P

    here = _P(__file__).resolve().parent
    comp = directional_coupler()
    comp.write_gds(str(here / "device.gds"), with_metadata=False)
    arms = {"top": arm_lengths[0], "bottom": arm_lengths[1]}
    (here / "lengths.json").write_text(
        json.dumps(
            {"arms": arms, "delta_length_um": abs(arms["top"] - arms["bottom"])}, indent=2
        )
    )
    print("wrote device.gds", comp.bbox(), "arms", arms)
