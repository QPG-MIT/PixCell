"""final8 — folded multi-turn delay line (two-arm spiral), central window.

Recreated from data/agents/paper_swap/final8/device_bw.png at the calibrated
absolute scale of footprint_um = [120, 4].

Topology (measured from the silhouette, see recreation_log.json):
  five transverse turns on a uniform pitch, mirror-symmetric about the field
  axis.  The central turn is the spiral's crossover bus and runs straight
  across the whole window; the two turns above the axis fold UP and the two
  below fold DOWN, at both ends, on circular arcs whose cores widen as they
  leave the window.  Turns alternate cross-section: the 1st and 3rd off the
  axis carry `n_rails - 1` longitudinal slots that split the wide core into
  rails (higher-order-mode stripping in a low-loss wide core); the 2nd is a
  solid slab.  The window is a crop — the folds and the bus continue outside
  it — so the geometry is clipped to the declared footprint with a boolean.

Primitives only: gf.Path + extrude / extrude_transition (taper), rectangle,
boolean.  No gf.components device stencils, no raw polygons.
"""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np

# ======================== tunables (top-level) =============================
# --- field / declared footprint --------------------------------------------
device_length = 120.0      # um   x extent of the drawn window  (footprint_um[0])
device_width = 4.0         # um   y extent of the drawn window  (footprint_um[1])

# --- function knobs ---------------------------------------------------------
core_width = 0.472         # um   transverse width of one turn's core
turn_pitch = 0.5017        # um   centre-to-centre pitch of the turns (delay per area)
n_rails = 5                # -    rails per segmented turn
rail_width = 0.068         # um   width of one rail in a segmented turn
slot_width = 0.032         # um   longitudinal slot width in a segmented turn
straight_length = 99.10    # um   straight run of each folded turn (delay per turn)
segment_start = 9.59       # um   x where the longitudinal segmentation begins
bend_radius_1 = 11.27      # um   fold radius, 1st turn off the axis
bend_radius_2 = 6.14       # um   fold radius, 2nd turn off the axis
leg_width_1 = 0.70         # um   core width where the 1st fold leaves the window
leg_width_2 = 0.75         # um   core width where the 2nd fold leaves the window
leg_flare_exp = 1.2        # -    exponent of the core->leg flare along a fold arc
axis_offset = -0.0022      # um   turn-stack centre relative to the window centre
bus_offset = -0.0051       # um   central bus offset from the turn-stack centre
rail_stack_offset = 0.0006 # um   rail stack offset from its turn's core centreline
delta_length = 0.0         # um   designed path imbalance, upper vs lower 1st fold
arc_points = 64            # -    polyline resolution of one fold arc
layer = (1, 0)

# ============================== derived ====================================
# NB every extruded width above must be an even number of dbu (2 nm) — kfactory
# rejects odd widths so that extrusions stay symmetric about their centreline.
turn_gap = turn_pitch - core_width       # um  physical gap between adjacent turns
rail_pitch = rail_width + slot_width
rail_stack = n_rails * rail_width + (n_rails - 1) * slot_width
axis_y = device_width / 2.0 + axis_offset
x_fold = (device_length - straight_length) / 2.0

# path lengths measured from the gf.Path objects at build time (never entered)
MEASURED_ARMS: dict[str, float] = {}


# ============================== helpers ====================================
def _arc_points(x_tangent, y_centre, radius, sign, y_from, y_to, n=arc_points):
    """Circular arc, horizontal-tangent at (x_tangent, y_centre), curving toward
    +y (sign=+1) or -y (sign=-1) and running toward decreasing x."""
    cy = y_centre + sign * radius

    def phi(y):
        return float(np.arccos(np.clip(abs(cy - y) / radius, -1.0, 1.0)))

    phis = np.linspace(phi(y_from), phi(y_to), n)
    return np.c_[x_tangent - radius * np.sin(phis), cy - sign * radius * np.cos(phis)]


def _mirror_x(pts):
    return np.c_[device_length - pts[:, 0], pts[:, 1]]


def _straight(comp, y_centre, x0, x1, width):
    """Extrude one straight centreline; return its measured gf.Path length."""
    path = gf.Path([(x0, y_centre), (x1, y_centre)])
    comp.add_ref(gf.path.extrude(path, layer=layer, width=width))
    return path.length()


def _straight_run(comp, y_centre, x0, x1, seg_from=None, seg_to=None):
    """Straight run of one turn.  Solid when seg_from is None, otherwise solid
    core out to seg_from / seg_to and split into n_rails in between."""
    if seg_from is None:
        return _straight(comp, y_centre, x0, x1, core_width)

    a, b = max(x0, seg_from), min(x1, seg_to)
    for xa, xb in ((x0, a), (b, x1)):
        if xb - xa > 1e-9:
            _straight(comp, y_centre, xa, xb, core_width)
    for k in range(n_rails):
        y_rail = (y_centre + rail_stack_offset - rail_stack / 2.0
                  + k * rail_pitch + rail_width / 2.0)
        _straight(comp, y_rail, a, b, rail_width)
    return gf.Path([(x0, y_centre), (x1, y_centre)]).length()


def _slot_offsets():
    """y offsets of the n_rails - 1 slot centrelines from a turn's core centreline."""
    return [rail_stack_offset - rail_stack / 2.0 + k * rail_pitch
            + rail_width + slot_width / 2.0 for k in range(n_rails - 1)]


def _fold_slots(comp, y_centre, radius, x_tangent, up):
    """The slots of a segmented turn continue as concentric arcs into the fold,
    from the straight run's end (x_tangent) out to x = segment_start, where the
    rails merge back into one solid core.  Extruded here, subtracted later."""
    sign = 1 if up else -1
    cy = y_centre + sign * radius
    for offset in _slot_offsets():
        r_slot = radius - sign * offset
        psi_end = float(np.arcsin(np.clip((x_tangent - segment_start) / r_slot, -1.0, 1.0)))
        psis = np.linspace(0.0, psi_end, max(8, arc_points // 4))
        pts = np.c_[x_tangent - r_slot * np.sin(psis), cy - sign * r_slot * np.cos(psis)]
        for arc in (pts, _mirror_x(pts)):
            comp.add_ref(gf.path.extrude(gf.Path(arc), layer=layer, width=slot_width))


def _folds(comp, y_centre, radius, leg_width, x_tangent, up):
    """Both folds of one turn: a tapered arc out to the window edge plus the
    clipped-away overshoot that keeps the leg full-width at the edge.
    Returns the in-window arc length summed over the two ends."""
    sign = 1 if up else -1
    y_edge = device_width if up else 0.0
    y_over = y_edge + sign * leg_width
    taper = gf.path.transition(
        gf.cross_section.cross_section(width=core_width, layer=layer),
        gf.cross_section.cross_section(width=leg_width, layer=layer),
        width_type=lambda t, w1, w2: w1 + (w2 - w1) * np.asarray(t) ** leg_flare_exp,
    )
    in_window = 0.0
    for mirror in (False, True):
        arc = _arc_points(x_tangent, y_centre, radius, sign, y_centre, y_edge)
        over = _arc_points(x_tangent, y_centre, radius, sign, y_edge, y_over)
        if mirror:
            arc, over = _mirror_x(arc), _mirror_x(over)
        p_arc, p_over = gf.Path(arc), gf.Path(over)
        comp.add_ref(gf.path.extrude_transition(p_arc, taper))
        comp.add_ref(gf.path.extrude(p_over, layer=layer, width=leg_width))
        in_window += p_arc.length()
    return in_window


# =============================== device ====================================
@gf.cell
def delay_line_window() -> gf.Component:
    raw = gf.Component()
    slots = gf.Component()
    MEASURED_ARMS.clear()

    # central turn — the spiral's crossover bus: straight across the whole
    # window, segmented over its entire visible run (its folds are off-crop).
    _straight_run(raw, axis_y + bus_offset, 0.0, device_length, 0.0, device_length)

    # the four folded turns, in mirror-symmetric pairs about the axis
    for k, (radius, leg_width, segmented) in enumerate(
        ((bend_radius_1, leg_width_1, False),
         (bend_radius_2, leg_width_2, True)),
        start=1,
    ):
        for up in (True, False):
            y_centre = axis_y + (k * turn_pitch if up else -k * turn_pitch)
            extra = delta_length if (up and k == 1) else 0.0
            x_tan = x_fold - extra / 2.0
            seg = (segment_start, device_length - segment_start) if segmented else (None, None)
            length = _straight_run(raw, y_centre, x_tan, device_length - x_tan, *seg)
            length += _folds(raw, y_centre, radius, leg_width, x_tan, up)
            if segmented and x_tan - segment_start > 1e-9:
                _fold_slots(slots, y_centre, radius, x_tan, up)
            if k == 1:
                MEASURED_ARMS["fold_upper" if up else "fold_lower"] = length

    # the segmentation runs a little way into each fold before the rails merge
    core = gf.boolean(raw, slots, operation="not", layer=layer)
    # the window is a crop: clip everything to the declared footprint
    frame = gf.components.rectangle(size=(device_length, device_width), layer=layer)
    return gf.boolean(core, frame, operation="and", layer=layer)


if __name__ == "__main__":
    out = Path(__file__).resolve().parent
    component = delay_line_window()
    # with_metadata=False: kfactory's $$$CONTEXT_INFO$$$ cell otherwise becomes the
    # only top-level cell, which hides the geometry from area-based verifiers.
    component.write_gds(out / "device.gds", with_metadata=False)

    arms = dict(MEASURED_ARMS)
    (out / "lengths.json").write_text(
        json.dumps(
            {
                "arms": arms,
                "delta_length_um": abs(arms["fold_upper"] - arms["fold_lower"]),
            },
            indent=2,
        )
    )
    print("bbox um:", component.dbbox())
    print("arms:", arms)
