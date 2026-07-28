"""Adiabatic (width-mismatched) 2x2 directional coupler, primitives only.

Two waveguides run from well-separated ports through S-bends into a long
interaction section where their widths counter-taper (top narrows, bottom
widens) at fixed centerlines and near-constant edge-to-edge gap, then S-bend
back out. Catalog components (straight, taper) plus gf.Path + extrude for the
S-bends. Layer (1, 0). GDSFactory 9.20.7.

The source figure strokes the S-bends with near-constant PIXEL width on a
11.7x vertically exaggerated scale, so the bends' vertical footprint fattens
toward mid-bend. The bend extrusion therefore carries a measured width bump
w(u) = base(u) + amp * (sin(pi u)^2)^q on top of the end widths; amp/q were
fitted per bend from the target ink and are tunables like everything else.

Frame: x = 0 at the left port tips, y = 0 at the footprint vertical center.
"""

import json
from pathlib import Path as FsPath

import numpy as np
import gdsfactory as gf
from gdsfactory.cross_section import Section

# ---------------- tunables (um) ----------------
# Function knobs of the coupler
coupling_length = 55.6   # shared interaction-section length (transfer length)
coupling_gap = 0.154     # edge-to-edge gap at the taper midpoint
w_top_c1 = 0.428         # top guide width entering the interaction section
w_top_c2 = 0.312         # top guide width leaving it
w_bot_c1 = 0.184         # bottom guide width entering
w_bot_c2 = 0.296         # bottom guide width leaving
# Port / routing geometry (widths in even nm: kfactory grid rule)
gap_mid_y = -0.043       # y of the gap midline in the interaction section
w_port_tl = 0.346        # access-guide widths
w_port_bl = 0.270
w_port_tr = 0.310
w_port_br = 0.298
y_port_tl = 1.735        # port centerline heights
y_port_bl = -1.713
y_port_tr = 1.835
y_port_br = -1.832
# Access straight lengths (per guide; left tips both at x = 0)
port_in_top = 18.38
port_in_bot = 19.24
port_out_top = 18.42
port_out_bot = 18.81
# Per-guide interaction-length trim (layout detail, not the function knob)
taper_extra_top = -0.4
taper_extra_bot = 0.4
# S-bend horizontal extents (per bend)
sbend_dx_tl = 13.53
sbend_dx_tr = 14.47
sbend_dx_bl = 12.14
sbend_dx_br = 13.81
# S-bend width-bump amplitude/sharpness (fitted from the target stroke)
bump_amp_tl = 0.879
bump_q_tl = 1.88
bump_amp_tr = 0.786
bump_q_tr = 3.5
bump_amp_bl = 0.514
bump_q_bl = 6.0
bump_amp_br = 0.716
bump_q_br = 3.73

LAYER = (1, 0)
_NPTS = 201

# Derived interaction-section centerlines: the gap knob is exact at the taper
# midpoint, so the centerlines follow from gap + mean taper widths.
w_top_mid = (w_top_c1 + w_top_c2) / 2
w_bot_mid = (w_bot_c1 + w_bot_c2) / 2
y_coup_top = gap_mid_y + coupling_gap / 2 + w_top_mid / 2
y_coup_bot = gap_mid_y - coupling_gap / 2 - w_bot_mid / 2


def _xs(width: float):
    return gf.cross_section.cross_section(width=width, layer=LAYER)


def _smoothstep(u):
    return 3 * u**2 - 2 * u**3


@gf.cell
def _sbend(dx: float, dy: float, w_l: float, w_r: float, amp: float, q: float) -> gf.Component:
    """S-bend as a smoothstep centerline extruded with the measured width bump."""
    u = np.linspace(0.0, 1.0, _NPTS)
    pts = np.column_stack([dx * u, dy * _smoothstep(u)])
    path = gf.Path(pts)

    def width_fn(t):
        base = w_l + (w_r - w_l) * _smoothstep(t)
        return base + amp * (np.sin(np.pi * t) ** 2) ** q

    section = Section(width=w_l, layer=LAYER, port_names=("o1", "o2"), width_function=width_fn)
    c = path.extrude(gf.CrossSection(sections=(section,)))
    c.info["path_length"] = float(path.length())
    return c


@gf.cell
def _guide(
    y_port_l: float,
    y_port_r: float,
    w_port_l: float,
    w_port_r: float,
    w_c1: float,
    w_c2: float,
    y_coup: float,
    len_in: float,
    len_out: float,
    taper_len: float,
    dx_l: float,
    dx_r: float,
    amp_l: float,
    q_l: float,
    amp_r: float,
    q_r: float,
) -> gf.Component:
    """One waveguide: straight - S-bend - counter-tapered straight - S-bend - straight."""
    c = gf.Component()
    s_in = c.add_ref(gf.components.straight(length=len_in, cross_section=_xs(w_port_l)))
    s_in.dmove((0, y_port_l))
    b_in = c.add_ref(_sbend(dx_l, y_coup - y_port_l, w_port_l, w_c1, amp_l, q_l))
    b_in.dmove((len_in, y_port_l))
    tap = c.add_ref(gf.components.taper(length=taper_len, width1=w_c1, width2=w_c2, layer=LAYER))
    tap.dmove((len_in + dx_l, y_coup))
    b_out = c.add_ref(_sbend(dx_r, y_port_r - y_coup, w_c2, w_port_r, amp_r, q_r))
    b_out.dmove((len_in + dx_l + taper_len, y_coup))
    s_out = c.add_ref(gf.components.straight(length=len_out, cross_section=_xs(w_port_r)))
    s_out.dmove((len_in + dx_l + taper_len + dx_r, y_port_r))
    c.info["path_length"] = (
        len_in
        + float(b_in.cell.info["path_length"])
        + taper_len
        + float(b_out.cell.info["path_length"])
        + len_out
    )
    return c


@gf.cell
def adiabatic_directional_coupler() -> gf.Component:
    c = gf.Component()
    top = c.add_ref(
        _guide(
            y_port_tl, y_port_tr, w_port_tl, w_port_tr, w_top_c1, w_top_c2, y_coup_top,
            port_in_top, port_out_top, coupling_length + taper_extra_top,
            sbend_dx_tl, sbend_dx_tr, bump_amp_tl, bump_q_tl, bump_amp_tr, bump_q_tr,
        )
    )
    bot = c.add_ref(
        _guide(
            y_port_bl, y_port_br, w_port_bl, w_port_br, w_bot_c1, w_bot_c2, y_coup_bot,
            port_in_bot, port_out_bot, coupling_length + taper_extra_bot,
            sbend_dx_bl, sbend_dx_br, bump_amp_bl, bump_q_bl, bump_amp_br, bump_q_br,
        )
    )
    c.info["arm_top_um"] = float(top.cell.info["path_length"])
    c.info["arm_bot_um"] = float(bot.cell.info["path_length"])
    return c


if __name__ == "__main__":
    out_dir = FsPath(__file__).resolve().parent
    component = adiabatic_directional_coupler()

    arm_top = float(component.info["arm_top_um"])
    arm_bot = float(component.info["arm_bot_um"])
    lengths = {
        "arms": {"top": arm_top, "bottom": arm_bot},
        "delta_length_um": abs(arm_top - arm_bot),
        "coupler": {
            "length_um": coupling_length,
            "gap_um": (y_coup_top - w_top_mid / 2) - (y_coup_bot + w_bot_mid / 2),
            "width_um": (w_top_mid + w_bot_mid) / 2,
        },
        "note": "arms include S-bend arc lengths from the extruded paths; "
        "coupler gap/width evaluated at the taper midpoint",
    }
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    component.write_gds(out_dir / "device.gds")
