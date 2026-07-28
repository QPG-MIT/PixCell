r"""final5 -- subwavelength-grating (SWG) side-coupled waveguide filter.

Topology (see recreation_log.json for the full reading of the figure)::

    ......----[ 56 SWG segments ]----____                  <- SWG arm  (port A)
                                         \  U-turn
    <|=======================================/             <- return bar + terminator
    ==============================================         <- continuous bus
            /=======================================|>     <- terminator + return bar
    U-turn /
    ____----[ 56 SWG segments ]----.......                 <- SWG arm  (port B)

A continuous strip "bus" waveguide runs down the middle.  Above and below it,
at a uniform gap, sit two identical periodically segmented (subwavelength
grating) waveguides.  The periodic index modulation supplies the momentum that
phase-matches the SWG Bloch mode to the bus mode, so power transfers between
them over the interaction length at the wavelength set by the pitch.  Each SWG
arm is launched through a long adiabatic tapered routing bend (the strip -> SWG
mode converter, cropped by the figure frame) and, at its far end, folded
through a 180 degree U-turn into a return bar that dies in a truncated inverse
taper -- a terminator for the un-transferred power.

Frame note: the supplied calibration maps a 3649 x 1134 px figure onto an
18.24 x 0.70 um footprint, i.e. it scales x and y by DIFFERENT factors
(200.05 px/um vs 1620 px/um).  The layout frame is therefore compressed
8.098x in y relative to the drawing, and every shape that is round in the
figure is an ellipse here.  ``figure_aspect`` carries that ratio so the
routing-bend taper can be specified the way it is drawn.  Transverse
dimensions sit on the 1 nm database grid (gdsfactory 9.20.7, dbu = 0.001 um),
which is 0.62 figure-pixels here.

Primitives only: rectangle, taper, ellipse (+ boolean), gf.Path + extrude.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import gdsfactory as gf
from gdsfactory.cross_section import CrossSection, Section

LAYER = (1, 0)

# ============================== TUNABLES (um) ==============================
# --- the coupler: subwavelength grating, the function-defining section ------
swg_period_um = 0.155167465          # pitch -- sets the phase-matching wavelength
swg_duty = 0.708718                  # segment length / pitch -> SWG Bloch index
swg_periods = 56                     # interaction length = periods * pitch
swg_width_um = 0.050                 # transverse width of each SWG segment
swg_gap_um = 0.018                   # bus edge -> SWG edge: sets kappa
swg_start_um = 4.503765420           # x of the first segment's leading edge

# --- the bus: continuous strip waveguide the SWG arms couple to ------------
bus_width_um = 0.026                 # bus mode index (other half of phase matching)
bus_length_um = 14.025405300         # through-path length  [VERIFIED KNOB]
bus_start_um = 1.941517790

# --- 180 degree fold (elliptical in this anisotropic frame) ----------------
uturn_extent_um = 1.447603180        # horizontal semi-axis of the outer boundary
uturn_inner_extent_um = 1.139187720  # horizontal semi-axis of the inner boundary
uturn_inner_dx_um = 0.125965470      # inner ellipse centre, displaced inward
uturn_lead_top_um = 0.849811600      # SWG lead: grating -> fold plane, top arm
uturn_lead_bot_um = 0.501702500      # ... bottom arm (the two arms differ in the drawing)

# --- return bar + terminator ----------------------------------------------
bar_width_um = 0.066                 # the returning guide is wider than the SWG lead
bar_offset_top_um = 0.308            # bar centre offset from the device axis, top arm
bar_offset_bot_um = 0.305            # ... bottom arm (the drawing is 4.5 px asymmetric)
term_taper_um = 1.507086870          # terminator taper length
term_tip_width_um = 0.008            # truncated tip width -> residual back-reflection
term_tip_x_top_um = 2.221091150      # terminator tip, top arm
term_tip_x_bot_um = 15.639612800     # terminator tip, bottom arm

# --- routing bends (strip -> SWG adiabatic converters, cropped by the frame)
route_lead_top_um = 1.383770680      # straight run on the SWG axis before the flare
route_lead_bot_um = 1.501988270
route_decay_um = 0.801280351         # e-folding length of the flare
route_c_top_um = 0.006301296         # flare amplitude, top-left bend
route_c_bot_um = 0.006475741         # flare amplitude, bottom-right bend
route_slope_max = 0.253678166        # slope the flare is capped at (straight run-out)
route_rise_top_um = 0.269986567      # total transverse excursion, top-left bend
route_rise_bot_um = 0.283851         # ... bottom-right bend (continued to the frame)
route_tip_width_um = 0.012963        # guide width at the cropped input tip
route_taper_um = 4.806180            # drawn length over which tip -> SWG width

# --- frame ----------------------------------------------------------------
figure_aspect = 8.097771             # y-compression of the layout frame vs the drawing

# ============================== fixed build settings =======================
ARC_DEG = 0.25                       # ellipse angular resolution
ROUTE_PTS = 1201                     # sample points per routing-bend path
CUT_BOX_UM = 2.0                     # half-plane cutter, comfortably over the fold

# ============================== derived ====================================
swg_tooth_um = swg_period_um * swg_duty
swg_gap_len_um = swg_period_um - swg_tooth_um
swg_span_um = (swg_periods - 1) * swg_period_um + swg_tooth_um
swg_end_um = swg_start_um + swg_span_um
swg_offset_um = bus_width_um / 2.0 + swg_gap_um + swg_width_um / 2.0
# the fold plane rides on the end of the grating, so the pitch knob stays physical
uturn_x_top_um = swg_end_um + swg_gap_len_um + uturn_lead_top_um
uturn_x_bot_um = swg_start_um - swg_gap_len_um - uturn_lead_bot_um
arm_edge_um = swg_offset_um - swg_width_um / 2.0        # outer edge of the SWG lead
arm_inner_um = swg_offset_um + swg_width_um / 2.0       # inner edge of the SWG lead


def _bar_edge(bar_offset_um: float) -> float:
    """Outer edge of the return bar, measured from the device axis."""
    return bar_offset_um + bar_width_um / 2.0


def _section(width: float, width_function=None) -> CrossSection:
    """Portless cross-section (transverse dimensions here are odd multiples of dbu)."""
    return CrossSection(
        sections=(
            Section(
                width=width,
                layer=LAYER,
                port_names=(None, None),
                width_function=width_function,
            ),
        )
    )


@gf.cell
def box(length: float, width: float) -> gf.Component:
    """An axis-aligned straight section, origin at its centre."""
    path = gf.Path(np.array([[-length / 2.0, 0.0], [length / 2.0, 0.0]]))
    return gf.path.extrude(path, cross_section=_section(width))


@gf.cell
def uturn(bar_offset_um: float, x_sign: float, y_sign: float) -> gf.Component:
    """180 degree fold as a half elliptical annulus.

    Both boundaries are pinned to the straights they join at the fold plane:
    the outer ellipse is tangent to the OUTER edges of the bar and of the SWG
    lead (so it is centred on the fold plane), and the inner ellipse -- pushed
    inward by ``uturn_inner_dx_um`` so the fold is thicker at 3 o'clock than on
    the straights -- is sized to cross the INNER edges of the bar and lead
    exactly at that same plane.  The annulus therefore widens from the SWG lead
    width to the (thicker) bar width as it comes round, with no step at either
    junction.  Returned centred on its fold plane at the origin, opening toward
    ``x_sign``, arm side toward ``-y_sign``.
    """
    b_out = (_bar_edge(bar_offset_um) - arm_edge_um) / 2.0
    bar_inner_um = bar_offset_um - bar_width_um / 2.0
    # the inner ellipse is off-centre in x, so it must be scaled up to still
    # hit the straights' inner edges at x = 0 (the fold plane)
    chord = np.sqrt(1.0 - (uturn_inner_dx_um / uturn_inner_extent_um) ** 2)
    b_in = (bar_inner_um - arm_inner_um) / (2.0 * chord)
    dy_in = (_bar_edge(bar_offset_um) + arm_edge_um) / 2.0 - (bar_inner_um + arm_inner_um) / 2.0

    outer = gf.Component()
    outer.add_ref(
        gf.components.ellipse(
            radii=(uturn_extent_um, b_out), angle_resolution=ARC_DEG, layer=LAYER
        )
    )
    inner = gf.Component()
    ref = inner.add_ref(
        gf.components.ellipse(
            radii=(uturn_inner_extent_um, b_in), angle_resolution=ARC_DEG, layer=LAYER
        )
    )
    ref.dmove((-x_sign * uturn_inner_dx_um, -y_sign * dy_in))
    annulus = gf.boolean(outer, inner, "not", layer=LAYER)

    keep = gf.Component()
    kref = keep.add_ref(
        gf.components.rectangle(size=(CUT_BOX_UM, CUT_BOX_UM), layer=LAYER, centered=True)
    )
    kref.dmove((x_sign * CUT_BOX_UM / 2.0, 0.0))
    return gf.boolean(annulus, keep, "and", layer=LAYER)


@gf.cell
def routing_bend(
    lead_um: float, c_um: float, rise_um: float, x_sign: float, y_sign: float
) -> gf.Component:
    """Adiabatic strip -> SWG routing bend, drawn from the SWG junction outward.

    Centreline: straight along the SWG axis for ``lead_um``, then an
    exponential flare ``c * (exp(v / decay) - 1)``, capped at
    ``route_slope_max`` where the drawing runs straight out through the figure
    edge.  Width: a linear taper over ``route_taper_um`` of DRAWN arc length
    (hence ``figure_aspect``) from the cropped tip width up to the SWG segment
    width, then uniform for the rest of the run into the grating.  Returned
    with its SWG junction at the origin, running toward ``x_sign`` / ``y_sign``.
    """
    u_join = lead_um + route_decay_um * np.log(route_slope_max * route_decay_um / c_um)
    off_join = route_slope_max * route_decay_um - c_um
    u_end = u_join + (rise_um - off_join) / route_slope_max

    u = np.linspace(0.0, u_end, ROUTE_PTS)
    v = np.clip(u - lead_um, 0.0, u_join - lead_um)
    flare = c_um * (np.exp(v / route_decay_um) - 1.0)
    grad = np.where(u <= lead_um, 0.0, (c_um / route_decay_um) * np.exp(v / route_decay_um))

    beyond = u > u_join
    off = np.where(beyond, off_join + route_slope_max * (u - u_join), flare)
    slope = np.where(beyond, route_slope_max, grad)

    x = x_sign * u
    y = y_sign * off
    path = gf.Path(np.column_stack([x, y]))

    # the width taper is uniform along the DRAWN arc length (y un-compressed)
    s_drawn = np.concatenate(
        [[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y) * figure_aspect))]
    )
    from_tip = s_drawn[-1] - s_drawn
    w_drawn = np.minimum(
        swg_width_um,
        route_tip_width_um + (swg_width_um - route_tip_width_um) * from_tip / route_taper_um,
    )
    # drawn perpendicular width -> layout vertical thickness -> layout perpendicular
    thickness = w_drawn * np.sqrt(1.0 + (slope * figure_aspect) ** 2)
    w_layout = thickness / np.sqrt(1.0 + slope**2)

    s_layout = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(x), np.diff(y)))])
    t_layout = s_layout / s_layout[-1]

    def width_function(t):
        return np.interp(np.asarray(t, dtype=float), t_layout, w_layout)

    return gf.path.extrude(path, cross_section=_section(swg_width_um, width_function))


def _straight(top: gf.Component, x0: float, x1: float, y: float, width: float) -> None:
    """Place an axis-aligned straight section spanning [x0, x1] at height ``y``."""
    lo, hi = sorted((x0, x1))
    ref = top.add_ref(box(hi - lo, width))
    ref.dmove(((lo + hi) / 2.0, y))


def _add_arm(
    top: gf.Component,
    y_sign: float,
    x_sign: float,
    bar_offset_um: float,
    uturn_x_um: float,
    tip_x_um: float,
    route_lead_um: float,
    route_c_um: float,
    route_rise_um: float,
) -> None:
    """One SWG arm: routing bend -> grating -> lead -> fold -> bar -> terminator.

    ``x_sign`` = +1 folds toward +x (routing bend enters from -x); -1 mirrors it.
    ``y_sign`` = +1 puts the arm above the bus.
    """
    y_arm = y_sign * swg_offset_um
    y_bar = y_sign * bar_offset_um

    # --- SWG lead: grating -> fold plane -----------------------------------
    lead_from = swg_end_um + swg_gap_len_um if x_sign > 0 else swg_start_um - swg_gap_len_um
    _straight(top, lead_from, uturn_x_um, y_arm, swg_width_um)

    # --- the fold ----------------------------------------------------------
    fold = top.add_ref(uturn(bar_offset_um, x_sign, y_sign))
    fold.dmove((uturn_x_um, y_sign * (_bar_edge(bar_offset_um) + arm_edge_um) / 2.0))

    # --- return bar: fold plane -> terminator ------------------------------
    taper_base = tip_x_um + x_sign * term_taper_um
    _straight(top, uturn_x_um, taper_base, y_bar, bar_width_um)

    term = top.add_ref(
        gf.components.taper(
            length=term_taper_um,
            width1=term_tip_width_um if x_sign > 0 else bar_width_um,
            width2=bar_width_um if x_sign > 0 else term_tip_width_um,
            layer=LAYER,
        )
    )
    term.dmove((min(tip_x_um, taper_base), y_bar))

    # --- routing bend feeding the grating ----------------------------------
    bend = top.add_ref(
        routing_bend(route_lead_um, route_c_um, route_rise_um, -x_sign, y_sign)
    )
    anchor = swg_start_um - swg_gap_len_um if x_sign > 0 else swg_end_um + swg_gap_len_um
    bend.dmove((anchor, y_arm))


@gf.cell
def device() -> gf.Component:
    """The full cell."""
    c = gf.Component()

    # --- bus (built as a path so its length is measured, not asserted) ------
    bus_path = gf.Path(
        np.array([[bus_start_um, 0.0], [bus_start_um + bus_length_um, 0.0]])
    )
    c.add_ref(gf.path.extrude(bus_path, cross_section=_section(bus_width_um)))

    # --- the two SWG segment rows ------------------------------------------
    tooth = box(swg_tooth_um, swg_width_um)
    for y_sign in (1.0, -1.0):
        row = c.add_ref(tooth, columns=swg_periods, rows=1, column_pitch=swg_period_um)
        row.dmove((swg_start_um + swg_tooth_um / 2.0, y_sign * swg_offset_um))

    # --- the two arms (180 degree rotations of one another) ----------------
    _add_arm(c, 1.0, 1.0, bar_offset_top_um, uturn_x_top_um, term_tip_x_top_um,
             route_lead_top_um, route_c_top_um, route_rise_top_um)
    _add_arm(c, -1.0, -1.0, bar_offset_bot_um, uturn_x_bot_um, term_tip_x_bot_um,
             route_lead_bot_um, route_c_bot_um, route_rise_bot_um)

    c.flatten()
    c.info["bus_length_um"] = float(bus_path.length())
    c.info["swg_span_um"] = float(swg_span_um)
    return c


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    comp = device()
    # with_metadata=False: kfactory's $$$CONTEXT_INFO$$$ cell REFERENCES the
    # device cell, which makes naive top-cell traversal (e.g.
    # homi.spec_optimization._layer_area) measure zero area.
    comp.write_gds(out / "device.gds", with_metadata=False)

    # Measurement contract: lengths derived from the built geometry, never
    # hand-entered.  The two co-propagating guides of the coupler are the
    # continuous bus and the segmented SWG section; delta_length_um is the
    # bus overhang beyond the interaction region.
    bus_len = float(comp.info["bus_length_um"])
    swg_len = float(comp.info["swg_span_um"])
    (out / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {"bus": bus_len, "swg_coupling_section": swg_len},
                "delta_length_um": bus_len - swg_len,
                "note": "arms = the two co-propagating guides of the SWG coupler: "
                        "the continuous bus and the segmented section it couples to.",
            },
            indent=2,
        )
    )
    print("bbox um:", comp.dbbox())
    print("delta_length_um:", bus_len - swg_len)
