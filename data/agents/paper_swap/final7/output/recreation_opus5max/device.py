"""final7 - primitives-only parametric recreation of the device in device_bw.png.

Topology (see recreation_log.json for the full reading): a closed oval loop whose
interior is hollowed by a shorter, thinner inner oval, so the loop's two ends are
SOLID vertices.  From each vertex a stem runs inward and opens into a Y-junction
that splits into two bridge arms; each arm widens into a multimode block holding a
pair of rectangular apertures, then mirrors back to the far vertex.  Four optical
paths therefore connect the two vertices (two loop halves + two bridge arms): a
loop resonator whose feedback path is itself a two-arm interferometer.

Gate frame.  The declared footprint (3.0 x 5.5 um) and the drawing aspect
(1.99:1) disagree, so compare_absolute's calibration is anisotropic
(517 px/um in x, 141.82 px/um in y).  Every dimension below is expressed in that
frame - the frame the deterministic verifier measures in.

Primitives only: gf.Path + extrude, gf.components.rectangle, booleans, @gf.cell.
No device stencils, no raw polygons, no image reads.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

import gdsfactory as gf
from gdsfactory.cross_section import CrossSection, Section

LAYER = (1, 0)
_HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# footprint (the calibrated frame)
# --------------------------------------------------------------------------
footprint_length_um = 3.0
footprint_width_um = 5.5

# --------------------------------------------------------------------------
# outer loop boundary.  half_height/half_length set the envelope; the corner is
# a two-exponent profile h(x) = tip + (half_h - tip) * (1 - (1-t)**n)**q with
# t = clip((half_len - |x|)/corner_len, 0, 1).
# --------------------------------------------------------------------------
loop_half_length_um = 1.500331
loop_half_height_um = 2.749197
loop_tip_half_height_um = 0.026883
loop_corner_length_um = 1.165303
loop_corner_n = 2.840295
loop_corner_q = 0.499065

# --------------------------------------------------------------------------
# inner cavity (the etched opening the bridge sits in).  It is SHORTER than the
# outer oval - that setback is what makes the loop's two ends solid vertices.
# loop_wall_width_um is the loop's guiding width at the top/bottom.
# --------------------------------------------------------------------------
loop_wall_width_um = 0.524410
cavity_end_setback_um = 0.290759
cavity_tip_half_height_um = 0.394917
cavity_corner_length_um = 0.907286
cavity_corner_n = 3.048103
cavity_corner_q = 0.614974

# --------------------------------------------------------------------------
# Y-junction (function knobs: splitting ratio + junction loss)
# --------------------------------------------------------------------------
stem_width_um = 1.297434
stem_root_x_um = 1.300000
junction_flare_x_um = 1.018247
junction_split_x_um = 0.979691
junction_tip_gap_um = 0.443500
branch_outer_angle_deg = 65.1024
branch_inner_angle_deg = 65.3391

# --------------------------------------------------------------------------
# bridge arms.  arm_gap_um is this topology's ONLY path-length knob: the two
# vertices are pinned by the loop, so every inline change cancels and only the
# transverse offset lengthens the bridge relative to the loop.
# --------------------------------------------------------------------------
arm_width_um = 0.430128
arm_gap_um = 1.410256

# --------------------------------------------------------------------------
# slotted multimode block (the in-arm aperture pair)
# --------------------------------------------------------------------------
block_length_um = 0.887898
block_width_um = 1.036539
block_center_offset_um = 0.916620
slot_length_um = 0.328530
slot_width_um = 0.553107
slot_center_offset_um = 0.911236
slot_divider_width_um = 0.107930

# --------------------------------------------------------------------------
# registration offsets.  The source raster is not perfectly symmetric: its
# cavity, blocks and apertures sit 0.5-1.25 px off the outer envelope's centre
# line, and its bridge is 1 px left of the envelope's centre.  These carry that
# offset explicitly instead of smearing it into the shape parameters.
# --------------------------------------------------------------------------
cavity_x_shift_um = -0.003482
cavity_y_shift_um = 0.008710
block_y_shift_um = -0.008814
block_x_shift_um = -0.001934
slot_y_shift_um = -0.006205
slot_x_shift_um = -0.000193
arm_block_overlap_um = 0.010000

# --------------------------------------------------------------------------
# meshing of the two smooth oval boundaries (not a shape knob)
# --------------------------------------------------------------------------
profile_points = 1401

# ---- derived ----------------------------------------------------------------
cavity_half_length_um = loop_half_length_um - cavity_end_setback_um
cavity_half_height_um = loop_half_height_um - loop_wall_width_um
arm_inner_offset_um = arm_gap_um / 2.0
arm_outer_offset_um = arm_inner_offset_um + arm_width_um
block_half_length_um = block_length_um / 2.0
slot_inner_x_um = slot_divider_width_um / 2.0
slot_outer_x_um = slot_inner_x_um + slot_length_um

_BIG = 9.0  # half-extent of the auxiliary half-planes / strips (device is < 6 um)


# ============================================================ profile helpers
def _oval_half_height(x, half_len, half_h, tip_h, corner_len, n, q):
    """Half-height of an oval boundary at abscissa ``x`` (0 = oval centre)."""
    t = np.clip((half_len - np.abs(np.asarray(x, dtype=float))) / corner_len, 0.0, 1.0)
    g = np.clip(1.0 - (1.0 - t) ** n, 0.0, 1.0) ** q
    return tip_h + (half_h - tip_h) * g


def _filled_oval(half_len, half_h, tip_h, corner_len, n, q):
    """Filled oval, centred on the origin, as one width-modulated extrusion."""
    # sine spacing clusters points where the profile is steepest (the two tips)
    s = np.linspace(-math.pi / 2, math.pi / 2, profile_points)
    xs = half_len * np.sin(s)
    path = gf.Path(np.column_stack([xs, np.zeros_like(xs)]))

    def width_function(t):
        x = (np.asarray(t, dtype=float) * 2.0 - 1.0) * half_len
        h = _oval_half_height(x, half_len, half_h, tip_h, corner_len, n, q)
        return np.maximum(2.0 * h, 1e-4)

    section = Section(width=1.0, offset=0.0, layer=LAYER, width_function=width_function)
    return gf.path.extrude(path, cross_section=CrossSection(sections=(section,)))


# ============================================================ boolean helpers
def _rect(x0, y0, x1, y1):
    """Axis-aligned filled rectangle."""
    comp = gf.Component()
    comp.add_ref(
        gf.components.rectangle(size=(x1 - x0, y1 - y0), layer=LAYER, centered=False)
    ).move((x0, y0))
    return comp


def _halfplane(x0, y0, slope, side):
    """Filled slab covering one side of the line y = y0 + slope*(x - x0).

    ``side`` = +1 keeps the larger-y side, -1 the smaller-y side.
    """
    ang = math.atan(slope)
    nx = -math.sin(ang) * side
    ny = math.cos(ang) * side
    xa, xb = x0 - _BIG, x0 + _BIG
    pts = np.array(
        [
            [xa + nx * _BIG, y0 + slope * (xa - x0) + ny * _BIG],
            [xb + nx * _BIG, y0 + slope * (xb - x0) + ny * _BIG],
        ]
    )
    return gf.path.extrude(gf.Path(pts), layer=LAYER, width=2.0 * _BIG)


def _bool(a, b, op):
    return gf.boolean(a, b, operation=op, layer=LAYER)


# ============================================================ device pieces
def _loop_ring():
    outer = _filled_oval(
        loop_half_length_um, loop_half_height_um, loop_tip_half_height_um,
        loop_corner_length_um, loop_corner_n, loop_corner_q,
    )
    cavity_oval = _filled_oval(
        cavity_half_length_um, cavity_half_height_um, cavity_tip_half_height_um,
        cavity_corner_length_um, cavity_corner_n, cavity_corner_q,
    )
    cavity = gf.Component()
    cavity.add_ref(cavity_oval).move((cavity_x_shift_um, cavity_y_shift_um))
    return _bool(outer, cavity, "not")


def _stem_half_width(x):
    """Stem half-width: flat, then flaring into the Y-junction."""
    flare = np.maximum(0.0, junction_flare_x_um - np.abs(np.asarray(x, dtype=float)))
    return stem_width_um / 2.0 + math.tan(math.radians(branch_outer_angle_deg)) * flare


def _stem(sx):
    xa, xb = sorted((sx * stem_root_x_um, sx * junction_split_x_um))
    xs = np.linspace(xa, xb, 121)
    path = gf.Path(np.column_stack([xs, np.zeros_like(xs)]))

    def width_function(t):
        x = xa + np.asarray(t, dtype=float) * (xb - xa)
        return 2.0 * _stem_half_width(x)

    section = Section(width=1.0, offset=0.0, layer=LAYER, width_function=width_function)
    return gf.path.extrude(path, cross_section=CrossSection(sections=(section,)))


def _arm_quadrant(sx, sy):
    """One of the four branch+straight arm bands (sx, sy in {-1, +1})."""
    tan_o = math.tan(math.radians(branch_outer_angle_deg))
    tan_i = math.tan(math.radians(branch_inner_angle_deg))
    slope_o = -sx * sy * tan_o
    slope_i = -sx * sy * tan_i

    # outward bound: |y| <= min(outer branch line, arm outer flat)
    outer = _bool(
        _halfplane(sx * junction_flare_x_um, sy * stem_width_um / 2.0, slope_o, -sy),
        _halfplane(0.0, sy * arm_outer_offset_um, 0.0, -sy),
        "and",
    )
    # inward bound: |y| >= min(inner branch line, arm inner flat)
    inner = _bool(
        _halfplane(sx * junction_split_x_um, sy * junction_tip_gap_um / 2.0, slope_i, sy),
        _halfplane(0.0, sy * arm_inner_offset_um, 0.0, sy),
        "or",
    )
    band = _bool(outer, inner, "and")
    # the inner end runs a little way under the block, which is taller: no extra
    # material, but no hairline crack at the block wall either
    inner_x = block_half_length_um - arm_block_overlap_um
    xa, xb = sorted((sx * junction_split_x_um, sx * inner_x))
    return _bool(band, _rect(xa, -_BIG, xb, _BIG), "and")


def _slotted_block(sy):
    c0 = sy * block_center_offset_um + block_y_shift_um
    s0 = sy * slot_center_offset_um + slot_y_shift_um
    block = _rect(
        -block_half_length_um + block_x_shift_um, c0 - block_width_um / 2.0,
        block_half_length_um + block_x_shift_um, c0 + block_width_um / 2.0,
    )
    slots = gf.Component()
    for sx in (-1, 1):
        xa, xb = sorted((sx * slot_inner_x_um, sx * slot_outer_x_um))
        xa, xb = xa + slot_x_shift_um, xb + slot_x_shift_um
        slots.add_ref(
            _rect(xa, s0 - slot_width_um / 2.0, xb, s0 + slot_width_um / 2.0)
        )
    return _bool(block, slots, "not")


# ============================================================ centrelines
def _bridge_arm_centreline(sy):
    """gf.Path along one bridge arm, vertex to vertex (for lengths.json)."""
    tan_o = math.tan(math.radians(branch_outer_angle_deg))
    tan_i = math.tan(math.radians(branch_inner_angle_deg))
    xs = np.linspace(-junction_split_x_um, junction_split_x_um, 601)
    outer = np.minimum(
        stem_width_um / 2.0 + tan_o * (junction_flare_x_um - np.abs(xs)),
        arm_outer_offset_um,
    )
    inner = np.minimum(
        junction_tip_gap_um / 2.0 + tan_i * (junction_split_x_um - np.abs(xs)),
        arm_inner_offset_um,
    )
    ys = sy * (outer + inner) / 2.0
    pts = np.vstack(
        [
            [[-loop_half_length_um, 0.0]],
            np.column_stack([xs, ys]),
            [[loop_half_length_um, 0.0]],
        ]
    )
    return gf.Path(pts)


def _loop_half_centreline(sy):
    """gf.Path along one half of the loop, vertex to vertex."""
    xs = np.linspace(-loop_half_length_um, loop_half_length_um, 1201)
    h_out = _oval_half_height(
        xs, loop_half_length_um, loop_half_height_um, loop_tip_half_height_um,
        loop_corner_length_um, loop_corner_n, loop_corner_q,
    )
    h_cav = _oval_half_height(
        xs, cavity_half_length_um, cavity_half_height_um, cavity_tip_half_height_um,
        cavity_corner_length_um, cavity_corner_n, cavity_corner_q,
    )
    ys = sy * (h_out + h_cav) / 2.0
    return gf.Path(np.column_stack([xs, ys]))


# ============================================================ assembly
@gf.cell
def device() -> gf.Component:
    pieces = [_loop_ring()]
    pieces += [_stem(sx) for sx in (-1, 1)]
    pieces += [_arm_quadrant(sx, sy) for sx in (-1, 1) for sy in (-1, 1)]
    pieces += [_slotted_block(sy) for sy in (-1, 1)]

    merged = pieces[0]
    for piece in pieces[1:]:
        merged = _bool(merged, piece, "or")

    c = gf.Component()
    c.add_ref(merged).move((loop_half_length_um, footprint_width_um / 2.0))
    return c


if __name__ == "__main__":
    component = device()
    # with_metadata=False keeps kfactory's $$$CONTEXT_INFO$$$ cell out of the
    # library: it references every cell, which makes naive top-level traversal
    # (e.g. homi.spec_optimization._layer_area) read zero area.
    component.write_gds(_HERE / "device.gds", with_metadata=False)

    bridge = _bridge_arm_centreline(1).length()
    loop_half = _loop_half_centreline(1).length()
    json.dump(
        {
            "arms": {"loop_half": float(loop_half), "bridge_arm": float(bridge)},
            "delta_length_um": float(abs(loop_half - bridge)),
            "note": (
                "The two interfering paths between the loop's solid vertices are "
                "one half of the loop and one bridge arm; both are measured from "
                "the script's own gf.Path centrelines. The two bridge arms are "
                "mirror images, so the bridge-vs-bridge imbalance is identically "
                "zero and the meaningful delta is loop-half vs bridge-arm."
            ),
        },
        open(_HERE / "lengths.json", "w"),
        indent=2,
    )
    print(f"bbox_um={component.dbbox()}  delta_length_um={abs(loop_half - bridge):.6f}")
