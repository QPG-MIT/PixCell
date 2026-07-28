"""Theta-type oval resonator with an internal two-arm interferometer.

Recreation of data/agents/paper_swap/final7/device_bw.png as a primitives-only,
parametric GDSFactory script (gdsfactory 9.20.7, layer (1,0)).

Topology
--------
A closed oval (stadium / rounded-rectangle) resonator loop.  Its left and right
lobes each feed a short wide stub that Y-splits into two waveguide arms; the two
arms run diagonally outward, flatten, and each passes through a widened bar
pierced by two rectangular windows (the phase / slot section) before recombining
at the mirrored Y-junction on the far side.  The chord of the ring is therefore a
balanced Mach-Zehnder, and the windows in each bar are what sets the per-arm
phase.  Exact 2-fold mirror symmetry about x = center_x_um and y = center_y_um.

Frame note
----------
The source figure's calibration is anisotropic (517 px/um in x, 141.8 px/um in
y).  In true microns the device is tall: 3.0 um wide by 5.5 um high, and the
interferometer runs vertically.  A waveguide of one constant width in the figure
therefore has a slope-dependent *perpendicular* width in microns.  The script
keeps the waveguide width as ONE knob (`arm_wg_width_um`, the width of the flat
run) and derives every sloped segment's perpendicular width from `figure_aspect`
via `_slope_width`, so the arm remains a single physical waveguide.

Primitives only: straight tapers (`gf.components.taper`), rectangles
(`gf.components.rectangle`), and booleans.  No gf.components device stencils, no
hand-written polygon vertex lists.
"""

from __future__ import annotations

import numpy as np
import gdsfactory as gf

LAYER = (1, 0)

# --------------------------------------------------------------------------
# frame
# --------------------------------------------------------------------------
footprint_x_um = 3.0
footprint_y_um = 5.5
center_x_um = 1.4990
center_y_um = 2.7500
figure_aspect = 517.0 / 141.8181818181818  # (px/um in x) / (px/um in y)

# --------------------------------------------------------------------------
# resonator loop.  Each silhouette is a superellipse-cornered rounded rectangle
#   half_width(y) = flat_half + corner_ax * (1 - |(y-cy)/semi_b|**n)**(1/n)
# --------------------------------------------------------------------------
loop_outer_flat_half_um = 0.4629
loop_outer_corner_ax_um = 1.0371
loop_outer_semi_b_um = 2.7500
loop_outer_power = 2.2500

loop_inner_flat_half_um = 0.4134
loop_inner_corner_ax_um = 0.7981
loop_inner_semi_b_um = 2.2176
loop_inner_power = 2.3331

loop_slices = 241  # taper-chain resolution of each filled silhouette

# --------------------------------------------------------------------------
# Y-junction: multimode stub that splits each lobe into the two arms
# --------------------------------------------------------------------------
internal_dy_um = 0.0  # offset of the interferometer mid-plane from the loop's
mzi_center_y_um = 2.7500 + internal_dy_um

splitter_vertex_x_um = 0.2979  # where the two arm centrelines meet
splitter_stem_x0_um = 0.2750  # stub root, buried in the loop wall
splitter_stem_x1_um = 0.5184  # stub throat, where the arms separate
splitter_stem_half_h_um = 0.6521

# --------------------------------------------------------------------------
# interferometer arms
# --------------------------------------------------------------------------
arm_wg_width_um = 0.4301  # waveguide width of the flat run (single knob)
arm_slope_fig = 0.6  # arm slope in the figure's isotropic frame
arm_offset_um = 0.9167  # |y - center| of the flat run (half the arm spacing)
arm_diag_overrun_um = 0.10  # how far the diagonal runs past the miter before clipping

# --------------------------------------------------------------------------
# phase section: a widened bar pierced by two rectangular windows
# --------------------------------------------------------------------------
bar_center_offset_um = 0.9097  # |y - center| of each bar
bar_width_um = 0.8917
bar_height_um = 1.0436
bar_rail_um = 0.2468  # solid rail above / below the windows
bar_end_wall_um = 0.0648  # outer wall of the bar
bar_slot_rib_um = 0.1103  # narrow rib between the two windows

# derived window geometry (kept derived so the bar always closes exactly)
bar_window_w_um = (bar_width_um - 2 * bar_end_wall_um - bar_slot_rib_um) / 2
bar_window_h_um = bar_height_um - 2 * bar_rail_um

arm_end_x_um = center_x_um - bar_width_um / 2  # arms land on the bar's outer wall

_JOIN_OVERLAP_UM = 0.001  # segment overlap that keeps taper chains watertight


# --------------------------------------------------------------------------
# helpers -- variable-width band built from a chain of straight tapers
# --------------------------------------------------------------------------
def _snap_width(w: float) -> float:
    """gdsfactory requires port widths to be an even number of dbu (0.002 um)."""
    return max(round(float(w) / 0.002) * 0.002, 0.002)


def _band(points, widths, layer=LAYER) -> gf.Component:
    """Variable-width band along a polyline, built only from straight tapers.

    Every segment but the last is extended by `_JOIN_OVERLAP_UM` (with its width
    linearly extrapolated) so consecutive trapezoids overlap rather than merely
    abut; abutting trapezoids leave sub-pixel seams that survive a boolean and
    show up as stray slivers in the raster.
    """
    c = gf.Component()
    n = len(points)
    for i in range(n - 1):
        x0, y0 = points[i]
        x1, y1 = points[i + 1]
        dx, dy = x1 - x0, y1 - y0
        length = float(np.hypot(dx, dy))
        if length < 1e-6:
            continue
        w0, w1 = float(widths[i]), float(widths[i + 1])
        if i < n - 2:
            # Overlap the next segment, extrapolating the width so the shared
            # edge still matches.  The overlap is clamped to half the segment:
            # near the caps of a superellipse the slices are far shorter than
            # the nominal overlap, and an unclamped extension would fling the
            # trapezoid (and its extrapolated width) past the silhouette.
            grow = min(_JOIN_OVERLAP_UM, 0.5 * length)
            w1 += (w1 - w0) * grow / length
            length += grow
        seg = gf.components.taper(
            length=round(length, 6),
            width1=_snap_width(w0),
            width2=_snap_width(w1),
            layer=layer,
        )
        ref = c << seg
        ref.rotate(float(np.degrees(np.arctan2(dy, dx))))
        ref.move((float(x0), float(y0)))
    return c


def _superellipse_fill(flat_half, corner_ax, semi_b, power, n=loop_slices):
    """Filled superellipse-cornered rounded rectangle, as a vertical taper chain."""
    u = np.linspace(-np.pi / 2, np.pi / 2, n)
    s = np.sin(u)
    ys = center_y_um + semi_b * s
    widths = 2.0 * (
        flat_half + corner_ax * np.clip(1.0 - np.abs(s) ** power, 0.0, 1.0) ** (1.0 / power)
    )
    pts = [(center_x_um, float(y)) for y in ys]
    return _band(pts, widths)


def _slope_width(slope_um: float) -> float:
    """Perpendicular width in um of the figure-frame waveguide on a sloped run.

    A waveguide of constant width in the (isotropic) figure frame has figure
    slope slope_um/figure_aspect; converting its vertical thickness back through
    the anisotropic y-stretch gives the perpendicular width below.  It reduces to
    arm_wg_width_um on the flat run.
    """
    m = float(slope_um)
    return float(
        arm_wg_width_um
        * np.sqrt(1.0 + (m / figure_aspect) ** 2)
        / np.sqrt(1.0 + m**2)
    )


def _arm_geometry(sign: int) -> dict[str, float]:
    """Centreline geometry of one arm -- the single source for both the extruded
    band and the length readout, so `lengths.json` can never drift from the GDS."""
    slope = arm_slope_fig * figure_aspect
    theta = float(np.arctan(slope))
    w_diag = _slope_width(slope)
    y_flat = mzi_center_y_um + sign * arm_offset_um
    x_corner = splitter_vertex_x_um + arm_offset_um / slope
    # x where the diagonal's outer edge meets the flat run's outer edge
    x_miter = splitter_vertex_x_um - (w_diag / 2) * np.sin(theta) + (
        arm_offset_um + arm_wg_width_um / 2 - (w_diag / 2) * np.cos(theta)
    ) / slope
    return {
        "slope": float(slope),
        "theta": theta,
        "w_diag": float(w_diag),
        "y_flat": float(y_flat),
        "x_corner": float(x_corner),
        "x_miter": float(x_miter),
        "diag_len": float((x_corner - splitter_vertex_x_um) / np.cos(theta)),
        "flat_len": float(arm_end_x_um - x_corner),
    }


def _arm(sign: int) -> gf.Component:
    """One interferometer arm: diagonal launch, mitered corner, flat run.

    The corner is a true miter, not a fillet: the diagonal band is run past the
    corner and the surplus beyond the flat run's outer edge is cut away.  A
    rounded blend cannot be used here -- under the anisotropic frame the band's
    half-width is ~50 px horizontally on the diagonal but ~30 px vertically on
    the flat run, so any finite blend radius bulges visibly outside the drawn
    edge.
    """
    g = _arm_geometry(sign)
    x_diag_end = g["x_corner"] + arm_diag_overrun_um
    diag = _band(
        [
            (splitter_vertex_x_um, mzi_center_y_um),
            (
                x_diag_end,
                mzi_center_y_um + sign * g["slope"] * (x_diag_end - splitter_vertex_x_um),
            ),
        ],
        [g["w_diag"], g["w_diag"]],
    )
    flat = _band(
        [(g["x_miter"], g["y_flat"]), (arm_end_x_um, g["y_flat"])],
        [arm_wg_width_um, arm_wg_width_um],
    )

    joined = gf.Component()
    joined << diag
    joined << flat

    # cut everything the diagonal overshoots past the flat run's outer edge
    y_edge = g["y_flat"] + sign * arm_wg_width_um / 2
    clip = gf.Component()
    cut = clip << gf.components.rectangle(
        size=(footprint_x_um, footprint_y_um), layer=LAYER, centered=True
    )
    cut.move((g["x_miter"] + footprint_x_um / 2, y_edge + sign * footprint_y_um / 2))
    return gf.boolean(joined, clip, "not", layer=LAYER)


def _phase_bar() -> gf.Component:
    """Widened bar pierced by two rectangular windows (rectangles + boolean)."""
    solid = gf.Component()
    r = solid << gf.components.rectangle(
        size=(bar_width_um, bar_height_um), layer=LAYER, centered=True
    )
    r.move((center_x_um, mzi_center_y_um + bar_center_offset_um))

    holes = gf.Component()
    for s in (-1, 1):
        h = holes << gf.components.rectangle(
            size=(bar_window_w_um, bar_window_h_um), layer=LAYER, centered=True
        )
        h.move(
            (
                center_x_um + s * (bar_slot_rib_um + bar_window_w_um) / 2,
                mzi_center_y_um + bar_center_offset_um,
            )
        )
    return gf.boolean(solid, holes, "not", layer=LAYER)


# --------------------------------------------------------------------------
# assembly
# --------------------------------------------------------------------------
@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    # 1. resonator loop = outer silhouette minus inner silhouette
    outer = _superellipse_fill(
        loop_outer_flat_half_um,
        loop_outer_corner_ax_um,
        loop_outer_semi_b_um,
        loop_outer_power,
    )
    inner = _superellipse_fill(
        loop_inner_flat_half_um,
        loop_inner_corner_ax_um,
        loop_inner_semi_b_um,
        loop_inner_power,
    )
    c << gf.boolean(outer, inner, "not", layer=LAYER)

    # 2. Y-junction stubs (left and right lobes)
    stem_len = splitter_stem_x1_um - splitter_stem_x0_um
    stem_mid = splitter_stem_x0_um + stem_len / 2
    for s in (-1, 1):
        stub = c << gf.components.rectangle(
            size=(stem_len, 2 * splitter_stem_half_h_um), layer=LAYER, centered=True
        )
        stub.move((center_x_um + s * (center_x_um - stem_mid), mzi_center_y_um))

    # 3. four interferometer arms (two per junction, mirrored left/right)
    for sign in (-1, 1):
        arm = _arm(sign)
        c << arm
        right = c << arm
        right.mirror_x(center_x_um)

    # 4. two phase sections (upper and lower arm)
    bar = _phase_bar()
    c << bar
    low = c << bar
    low.mirror_y(mzi_center_y_um)

    return c


def arm_lengths_um() -> dict[str, float]:
    """Optical path length of each interferometer arm, read off its centreline.

    Each arm runs vertex -> diagonal -> miter -> flat run -> phase bar -> flat
    run -> miter -> diagonal -> vertex, so its chord length is
    2*(diagonal + flat) + bar.  The numbers come from `_arm_geometry`, the same
    helper the bands are extruded from -- never hand entered.  The drawn device
    is a *balanced* MZI (the two arms are exact mirror images), so
    delta_length_um is zero at the figure's parameter values; it moves the
    moment the two arms' geometry is allowed to differ.
    """
    out = {}
    for name, sign in (("top", 1), ("bottom", -1)):
        g = _arm_geometry(sign)
        out[name] = float(2.0 * (g["diag_len"] + g["flat_len"]) + bar_width_um)
    return out


if __name__ == "__main__":
    import json

    comp = device()
    bb = comp.dbbox()
    print(
        f"bbox um: x {bb.left:.4f}..{bb.right:.4f} ({bb.right - bb.left:.4f})  "
        f"y {bb.bottom:.4f}..{bb.top:.4f} ({bb.top - bb.bottom:.4f})"
    )
    comp.write_gds("device.gds", with_metadata=False)

    arms = arm_lengths_um()
    with open("lengths.json", "w") as fh:
        json.dump(
            {"arms": arms, "delta_length_um": arms["top"] - arms["bottom"]}, fh, indent=2
        )
    print("wrote device.gds and lengths.json", arms)
