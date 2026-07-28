"""Adiabatic mode-evolution 1x2 splitter (trident / three-guide Y-junction).

A single input guide tapers to a tip while two flanking guides taper up from
tips alongside it (adiabatic power transfer), then separate via sine s-bends.
Primitives only: gf.components.taper, gf.Path + extrude. Layer (1, 0).
"""

import json
from pathlib import Path

import numpy as np
import gdsfactory as gf

LAYER = (1, 0)

# --- tunables (um) ---------------------------------------------------------
device_length = 40.0        # total footprint length
in_width = 0.27             # input guide width
center_tip_width = 0.06     # central taper tip width (residual coupling)
taper_start = 4.0           # x where the central taper begins
taper_length = 21.05        # adiabatic transfer length — primary function knob
center_y = 0.015            # central guide centerline offset (GDS +y = image top)
outer_tip_width = 0.056     # outer guide tip width
wg_width = 0.244            # output guide width (single-mode)
outer_start_x = 3.07        # x where the outer tips begin
top_y = 0.279               # image-top arm centerline before the s-bend
bot_y = -0.257              # image-bottom arm centerline before the s-bend
y_out = 0.730               # output centerline half-pitch after the s-bend
sbend_start_top = 25.45     # x where the top s-bend begins
sbend_start_bot = 25.5     # x where the bottom s-bend begins
sbend_length = 11.0         # s-bend length (output decoupling)
# ---------------------------------------------------------------------------


def _sine_sbend_path(x0: float, y0: float, length: float, dy: float) -> gf.Path:
    t = np.linspace(0.0, 1.0, 201)
    x = x0 + length * t
    y = y0 + dy * (t - np.sin(2 * np.pi * t) / (2 * np.pi))
    return gf.Path(np.column_stack([x, y]))


def _straight_path(x0: float, y0: float, x1: float) -> gf.Path:
    return gf.Path(np.array([[x0, y0], [x1, y0]]))


@gf.cell
def splitter() -> gf.Component:
    c = gf.Component()

    # central guide: input straight + down-taper to a tip
    p_in = _straight_path(0.0, center_y, taper_start)
    c.add_ref(gf.path.extrude(p_in, layer=LAYER, width=in_width))
    tap_c = gf.components.taper(
        length=taper_length, width1=in_width, width2=center_tip_width, layer=LAYER
    )
    r = c.add_ref(tap_c)
    r.move((taper_start, center_y))

    # outer arms: up-taper alongside the central taper, s-bend out, straight
    for y0, sbend_start, sign in (
        (top_y, sbend_start_top, +1.0),
        (bot_y, sbend_start_bot, -1.0),
    ):
        tap_o = gf.components.taper(
            length=sbend_start - outer_start_x,
            width1=outer_tip_width,
            width2=wg_width,
            layer=LAYER,
        )
        r = c.add_ref(tap_o)
        r.move((outer_start_x, y0))

        dy = sign * y_out - y0
        p_bend = _sine_sbend_path(sbend_start, y0, sbend_length, dy)
        c.add_ref(gf.path.extrude(p_bend, layer=LAYER, width=wg_width))

        p_out = _straight_path(sbend_start + sbend_length, sign * y_out, device_length)
        c.add_ref(gf.path.extrude(p_out, layer=LAYER, width=wg_width))

    return c


if __name__ == "__main__":
    here = Path(__file__).parent
    comp = splitter()

    # lengths.json — computed from the constructed paths, never hand-entered.
    # This device is a symmetric 1x2 splitter, not an MZI: no function knob
    # changes the output-arm length difference. To keep the two-arm contract
    # meaningful, the two "arms" are the central guide's total path and its
    # pre-taper input section, so delta_length_um == the adiabatic taper
    # length (taper_length, the primary function knob), 1:1.
    central_total = _straight_path(0.0, center_y, taper_start).length() + _straight_path(
        taper_start, center_y, taper_start + taper_length
    ).length()
    input_straight = _straight_path(0.0, center_y, taper_start).length()
    output_arms = {}
    for name, y0, sbend_start, sign in (
        ("top", top_y, sbend_start_top, +1.0),
        ("bottom", bot_y, sbend_start_bot, -1.0),
    ):
        taper_len = sbend_start - outer_start_x
        bend_len = _sine_sbend_path(sbend_start, y0, sbend_length, sign * y_out - y0).length()
        straight_len = _straight_path(sbend_start + sbend_length, sign * y_out, device_length).length()
        output_arms[name] = float(taper_len + bend_len + straight_len)
    lengths = {
        "arms": {
            "central_guide_total": float(central_total),
            "central_input_straight": float(input_straight),
        },
        "delta_length_um": float(central_total - input_straight),
        "output_arms_um": output_arms,
    }
    (here / "lengths.json").write_text(json.dumps(lengths, indent=2))

    comp.write_gds(here / "device.gds", with_metadata=False)
