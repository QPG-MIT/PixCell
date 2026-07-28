"""Dual grating-assisted contra-directional coupler (contra-DC).

A straight central bus waveguide with two identical corrugated (segmented /
sub-wavelength-grating) coupler arms mirrored above and below it.  Each arm
is a full signal path:

    curved adiabatic access taper  ->  periodically segmented coupling section
    ->  180 degree U-turn  ->  return guide  ->  sharp inverse-taper terminator

The grating supplies the momentum K = 2*pi/Lambda that phase-matches the
forward bus mode to the BACKWARD arm mode (beta_bus + beta_arm = K), so a
narrow band around that wavelength is coupled contra-directionally out of the
bus and into the arm; the U-turn plus radiative tip dumps the residual
co-propagating light without forming a Fabry-Perot cavity.

Primitives only: gf.Path + extrude (with an analytic width profile),
gf.components.rectangle, and a boolean subtraction for the corrugation.

Authoring frame
---------------
The supplied calibration is strongly anisotropic (200.05 px/um in x but
1620 px/um in y), so the device is authored by measuring the figure in pixels
and mapping each axis with its own scale.  A stroke of constant thickness in
the figure is therefore NOT a constant perpendicular stroke in device
coordinates; _perp_width_um() converts the figure-space thickness into the
perpendicular width the extrusion must use at every point along a path.
"""

import numpy as np
import gdsfactory as gf
from gdsfactory.cross_section import CrossSection, Section

LAYER = (1, 0)

# --- calibration (calibration.json) -----------------------------------------
PX_PER_UM_X = 200.05482456140354
PX_PER_UM_Y = 1620.0
X_ANCHOR_PX = 63.0     # render is LEFT-aligned: gds xmin -> this pixel column
Y_ANCHOR_PX = 1152.0   # y-flip reference (image row -> gds micron)

# =============================================================================
# top-level tunables (microns) - the function-defining knobs of the contra-DC
# =============================================================================

# -- the two phase-matched guides ------------------------------------------
bus_width_um = 0.0261728           # central bus waveguide width
arm_width_um = 0.0509877          # corrugated arm waveguide width
coupling_gap_um = 0.0169136       # bus edge <-> arm edge separation (kappa)

# -- the grating: sets the contra-directional phase-matching wavelength ------
grating_period_um = 0.1589058     # Lambda
grating_gap_um = 0.0364901        # low-index segment length (duty = 1 - gap/Lambda)
grating_periods = 57              # number of periods -> reflectivity / bandwidth
grating_start_um = 4.4167854      # x of the first low-index segment

# -- the central bus ---------------------------------------------------------
bus_start_um = 1.9444680
bus_length_um = 14.0261680        # <- knob-response witness (area = width x length)

# -- the 180 degree return bend ----------------------------------------------
uturn_x_semiaxis_um = 1.2896480   # top arm
uturn_y_semiaxis_um = 0.1257407
uturn_x_semiaxis_b_um = 1.3296280  # bottom arm
uturn_y_semiaxis_b_um = 0.1253704

# -- the radiative terminator (inverse taper) --------------------------------
terminator_width_um = 0.0679012
terminator_width_b_um = 0.0660494
terminator_taper_length_um = 1.5945615
uturn_apex_width_um = 0.0537037   # guide width at the apex of the 180 degree bend
terminator_tip_width_um = 0.0065432

# -- the adiabatic access taper ----------------------------------------------
access_tip_width_um = 0.0117284   # width at the facet
access_taper_rate = 0.0315        # half-width growth per unit arc (figure space)

# =============================================================================
# layout anchors, in figure pixels (measured from device_bw.png)
# =============================================================================
_BUS_Y_PX = 574.5

_UTURN_APEX_TOP_PX = 3117.0
_UTURN_APEX_BOT_PX = 608.0

_ACCESS_IN_END_PX = 700.0     # where the input access curve merges with the arm
_ACCESS_IN_PORT_PX = 63.0     # facet (figure edge)
_ACCESS_IN_SPAN_PX = 634.0
_ACCESS_IN_A = 27.70          # centreline offset d(r) = A * r * exp(k * r)
_ACCESS_IN_K = 2.770
_ACCESS_OUT_END_PX = 2960.0
_ACCESS_OUT_PORT_PX = 3615.4
_ACCESS_OUT_SPAN_PX = 690.0
_ACCESS_OUT_A = 20.82
_ACCESS_OUT_K = 3.334

_TERM_FULL_TOP_PX = 823.0     # where the terminator reaches full width
_TERM_FULL_BOT_PX = 2874.0

_GAP_HALF_SPAN_PX = 60.0      # vertical reach of the corrugation cut-outs
_RING_XC_OUT_PX = 11.0        # U-turn ring: ellipse centres sit just inside the seam
_RING_XC_IN_PX = 8.0
_SEAM_PX = 6.0                # straight guides overlap the ring at the seam
_ELLIPSE_RES = 0.2            # degrees
_N_ACCESS = 500
_N_STRAIGHT = 240
_N_BEND = 600
_N_TAPER = 160


# =============================================================================
# helpers
# =============================================================================
def _px_to_um(pts_px):
    """Figure pixels -> device microns (per-axis scale + y flip)."""
    x = (pts_px[:, 0] - X_ANCHOR_PX) / PX_PER_UM_X
    y = (Y_ANCHOR_PX - pts_px[:, 1]) / PX_PER_UM_Y
    return np.column_stack([x, y])


def _perp_width_um(pts_px, halfwidth_px):
    """Figure-space stroke thickness -> perpendicular width in device microns.

    With per-axis scales sx, sy and a figure-space tangent angle a, a stroke of
    figure thickness W maps to a band whose perpendicular width is
    W * sx * sy / sqrt((sx cos a)^2 + (sy sin a)^2).
    """
    d = np.gradient(pts_px, axis=0)
    a = np.arctan2(d[:, 1], d[:, 0])
    sx, sy = 1.0 / PX_PER_UM_X, 1.0 / PX_PER_UM_Y
    denom = np.sqrt((sx * np.cos(a)) ** 2 + (sy * np.sin(a)) ** 2)
    return 2.0 * np.asarray(halfwidth_px) * sx * sy / denom


def _extrude_px(pts_px, halfwidth_px):
    """Extrude a figure-space centreline with a varying figure-space thickness."""
    pts_px = np.asarray(pts_px, dtype=float)
    keep = np.concatenate([[True], np.any(np.abs(np.diff(pts_px, axis=0)) > 1e-9, axis=1)])
    pts_px = pts_px[keep]
    halfwidth_px = np.asarray(halfwidth_px, dtype=float)[keep]

    pts_um = _px_to_um(pts_px)
    width_um = _perp_width_um(pts_px, halfwidth_px)

    seg = np.sqrt(np.sum(np.diff(pts_um, axis=0) ** 2, axis=1))
    s = np.concatenate([[0.0], np.cumsum(seg)])
    t_nodes = s / s[-1]

    def _wf(t, _t=t_nodes, _w=width_um):
        return np.interp(np.asarray(t, dtype=float), _t, _w)

    section = Section(
        width=float(round(width_um.mean() / 0.002) * 0.002),  # port width: 2-dbu grid
        layer=LAYER,
        port_names=(None, None),
        width_function=_wf,
    )
    return gf.path.extrude(gf.Path(pts_um), cross_section=CrossSection(sections=(section,)))


def _access_curve(x_port, x_end, span, amp, k, y_arm, y_term, n):
    """Adiabatic access curve: centreline offset d(r) = amp * r * exp(k * r)."""
    x = np.linspace(x_port, x_end, n)
    r = np.abs(x_end - x) / span
    sign = 1.0 if y_term > y_arm else -1.0
    y = y_arm + sign * amp * r * np.exp(k * r)
    return np.column_stack([x, y])


def _feed_arm(y_arm, y_term, x_port, x_access_end, span, amp, k, x_bend,
              hw_arm, hw_access_tip):
    """Facet -> adiabatic access taper -> straight coupling section."""
    access = _access_curve(x_port, x_access_end, span, amp, k, y_arm, y_term, _N_ACCESS)
    straight = np.column_stack([
        np.linspace(x_access_end, x_bend, _N_STRAIGHT),
        np.full(_N_STRAIGHT, y_arm),
    ])
    pts = np.vstack([access, straight[1:]])
    ds = np.concatenate([[0.0], np.cumsum(np.sqrt(np.sum(np.diff(pts, axis=0) ** 2, axis=1)))])
    return pts, np.minimum(hw_access_tip + access_taper_rate * ds, hw_arm)


def _terminator(y_term, x_bend, x_term_full, x_term_tip, hw_term, hw_term_tip):
    """Return guide -> sharp inverse-taper radiative tip."""
    straight = np.column_stack([
        np.linspace(x_bend, x_term_full, _N_STRAIGHT),
        np.full(_N_STRAIGHT, y_term),
    ])
    taper = np.column_stack([
        np.linspace(x_term_full, x_term_tip, _N_TAPER),
        np.full(_N_TAPER, y_term),
    ])
    pts = np.vstack([straight, taper[1:]])
    hw = np.concatenate([
        np.full(len(straight), hw_term),
        np.linspace(hw_term, hw_term_tip, len(taper))[1:],
    ])
    return pts, hw


def _uturn(x_bend, x_out_apex, x_in_apex, y_out_lo, y_out_hi, y_in_lo, y_in_hi):
    """180 degree return bend as an elliptical ring, clipped to the bend side.

    In the anisotropic authoring frame the bend's radius of curvature at its
    apex (~0.012 um) is far smaller than its own width (~0.44 um), so a
    perpendicular extrusion of the centreline self-intersects.  The band is
    therefore built from its two boundaries directly: an outer and an inner
    ellipse (both measured off the figure), differenced and then clipped by a
    rectangle at the bend start, where the ring degenerates exactly into the
    straight guide cross-sections it must meet.
    """
    sign = 1.0 if x_out_apex > x_bend else -1.0
    out_yc, out_b = 0.5 * (y_out_lo + y_out_hi), 0.5 * (y_out_hi - y_out_lo)
    in_yc, in_b = 0.5 * (y_in_lo + y_in_hi), 0.5 * (y_in_hi - y_in_lo)
    out_xc = x_bend + sign * _RING_XC_OUT_PX
    in_xc = x_bend + sign * _RING_XC_IN_PX
    out_a = abs(x_out_apex - out_xc)
    in_a = abs(x_in_apex - in_xc)

    disc = gf.Component()
    disc.add_ref(gf.components.ellipse(
        radii=(out_a / PX_PER_UM_X, out_b / PX_PER_UM_Y),
        angle_resolution=_ELLIPSE_RES, layer=LAYER,
    )).dmove(_px_point(out_xc, out_yc))
    hole = gf.Component()
    hole.add_ref(gf.components.ellipse(
        radii=(in_a / PX_PER_UM_X, in_b / PX_PER_UM_Y),
        angle_resolution=_ELLIPSE_RES, layer=LAYER,
    )).dmove(_px_point(in_xc, in_yc))
    ring = gf.boolean(disc, hole, operation="not", layer=LAYER)

    reach = 3.0 * out_a / PX_PER_UM_X
    height = 2.0 * out_b / PX_PER_UM_Y + 0.02
    keep = gf.Component()
    ref = keep.add_ref(gf.components.rectangle(size=(reach, height), layer=LAYER))
    x0, y0 = _px_point(x_bend, out_yc + out_b)
    ref.dmove((x0 if sign > 0 else x0 - reach, y0 - 0.01))
    return gf.boolean(ring, keep, operation="and", layer=LAYER)


def _px_point(x_px, y_px):
    return ((x_px - X_ANCHOR_PX) / PX_PER_UM_X, (Y_ANCHOR_PX - y_px) / PX_PER_UM_Y)


@gf.cell
def contra_dc() -> gf.Component:
    c = gf.Component()

    hw_arm = 0.5 * arm_width_um * PX_PER_UM_Y
    hw_term = 0.5 * terminator_width_um * PX_PER_UM_Y
    hw_term_b = 0.5 * terminator_width_b_um * PX_PER_UM_Y
    hw_access_tip = 0.5 * access_tip_width_um * PX_PER_UM_Y
    hw_term_tip = 0.5 * terminator_tip_width_um * PX_PER_UM_Y
    hw_apex = 0.5 * uturn_apex_width_um * PX_PER_UM_Y
    taper_px = terminator_taper_length_um * PX_PER_UM_X

    arm_dy = 0.5 * (arm_width_um + bus_width_um) * PX_PER_UM_Y + coupling_gap_um * PX_PER_UM_Y
    y_arm_top = _BUS_Y_PX - arm_dy
    y_arm_bot = _BUS_Y_PX + arm_dy
    y_term_top = y_arm_top - 2.0 * uturn_y_semiaxis_um * PX_PER_UM_Y
    y_term_bot = y_arm_bot + 2.0 * uturn_y_semiaxis_b_um * PX_PER_UM_Y

    x_bend_top = _UTURN_APEX_TOP_PX - uturn_x_semiaxis_um * PX_PER_UM_X
    x_bend_bot = _UTURN_APEX_BOT_PX + uturn_x_semiaxis_b_um * PX_PER_UM_X

    arms = gf.Component()
    # top arm: facet on the left, U-turn on the right
    arms.add_ref(_extrude_px(*_feed_arm(
        y_arm_top, y_term_top, _ACCESS_IN_PORT_PX, _ACCESS_IN_END_PX,
        _ACCESS_IN_SPAN_PX, _ACCESS_IN_A, _ACCESS_IN_K, x_bend_top + _SEAM_PX, hw_arm, hw_access_tip)))
    arms.add_ref(_extrude_px(*_terminator(
        y_term_top, x_bend_top + _SEAM_PX, _TERM_FULL_TOP_PX,
        _TERM_FULL_TOP_PX - taper_px, hw_term, hw_term_tip)))
    arms.add_ref(_uturn(
        x_bend_top, _UTURN_APEX_TOP_PX + hw_apex, _UTURN_APEX_TOP_PX - hw_apex,
        y_term_top - hw_term, y_arm_top + hw_arm,
        y_term_top + hw_term, y_arm_top - hw_arm))
    # bottom arm: 180 degree partner, facet on the right, U-turn on the left
    arms.add_ref(_extrude_px(*_feed_arm(
        y_arm_bot, y_term_bot, _ACCESS_OUT_PORT_PX, _ACCESS_OUT_END_PX,
        _ACCESS_OUT_SPAN_PX, _ACCESS_OUT_A, _ACCESS_OUT_K, x_bend_bot - _SEAM_PX, hw_arm, hw_access_tip)))
    arms.add_ref(_extrude_px(*_terminator(
        y_term_bot, x_bend_bot - _SEAM_PX, _TERM_FULL_BOT_PX,
        _TERM_FULL_BOT_PX + taper_px, hw_term_b, hw_term_tip)))
    arms.add_ref(_uturn(
        x_bend_bot, _UTURN_APEX_BOT_PX - hw_apex, _UTURN_APEX_BOT_PX + hw_apex,
        y_arm_bot - hw_arm, y_term_bot + hw_term_b,
        y_arm_bot + hw_arm, y_term_bot - hw_term_b))

    # --- the corrugation: periodic low-index segments cut from both arms ----
    cuts = gf.Component()
    gap_w = grating_gap_um
    period = grating_period_um
    span = _GAP_HALF_SPAN_PX / PX_PER_UM_Y
    rect = gf.components.rectangle(size=(gap_w, 2 * span), layer=LAYER, centered=True)
    for arm_y in (y_arm_top, y_arm_bot):
        yc = (Y_ANCHOR_PX - arm_y) / PX_PER_UM_Y
        for i in range(int(grating_periods)):
            ref = cuts.add_ref(rect)
            ref.dmove((grating_start_um + (i + 0.5) * period - 0.5 * period + 0.5 * gap_w, yc))
    corrugated = gf.boolean(arms, cuts, operation="not", layer=LAYER)
    c.add_ref(corrugated)

    # --- the central bus ----------------------------------------------------
    bus = gf.components.rectangle(
        size=(bus_length_um, bus_width_um), layer=LAYER, centered=True
    )
    bus_ref = c.add_ref(bus)
    bus_ref.dmove((bus_start_um + 0.5 * bus_length_um,
                   (Y_ANCHOR_PX - _BUS_Y_PX) / PX_PER_UM_Y))
    return c


if __name__ == "__main__":
    comp = contra_dc()
    comp.write_gds("device.gds")
    b = comp.dbbox()
    print("bbox_um", b.left, b.bottom, b.right, b.top)
    print("size_um", b.right - b.left, b.top - b.bottom)
    print("y_px", Y_ANCHOR_PX - b.top * PX_PER_UM_Y, Y_ANCHOR_PX - b.bottom * PX_PER_UM_Y)
    print("x_px", X_ANCHOR_PX + b.left * PX_PER_UM_X, X_ANCHOR_PX + b.right * PX_PER_UM_X)
