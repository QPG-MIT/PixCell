"""
final7 recreation -- racetrack-ring-loaded balanced Mach-Zehnder interferometer.

Primitives only: gf.components.rectangle + gf.components.ellipse + gf.boolean
(outer/inner rounded rectangles -> ring frame; window subtraction), gf.Path +
extrude (the two MZI arms). Layer (1,0). Ends with write_gds. Also writes
lengths.json (arm centerline lengths, from the gf.Path point lists) for the
spec-evaluation contract in homi/spec_optimization.

All function-defining knobs are top-level `name = value` assignments.
"""
import json
import math
from pathlib import Path as FsPath

import gdsfactory as gf

LAYER = (1, 0)

# ================= TOP-LEVEL TUNABLES (function knobs) =================
# --- footprint (fills the calibration bbox; renderer stretches x by 3.65x) ---
device_length_um = 3.0      # x extent
device_width_um = 5.5       # y extent

# --- outer racetrack ring (resonant feedback loop): two concentric rounded
#     rectangles, outer minus inner-hole. The inner hole sets the ring<->MZI gap.
ring_outer_rx_um = 0.94     # outer corner radius (x)
ring_outer_ry_um = 2.50     # outer corner radius (y)
ring_hole_halfx_um = 0.98   # inner-hole half-width  (x); ring-to-MZI coupling gap
ring_hole_halfy_um = 2.22   # inner-hole half-height (y)
ring_inner_rx_um = 0.59     # inner-hole corner radius (x)
ring_inner_ry_um = 0.62     # inner-hole corner radius (y)

# --- Mach-Zehnder arms ---
arm_width_um = 0.44         # arm waveguide width
arm_sep_um = 1.834          # center-to-center vertical spacing of the two arms
splitter_len_um = 0.232     # x-length of the Y-junction fan-out (splitter/combiner)
splitter_gap_um = 0.958     # arm spacing where they meet the ring caps
port_x_um = 0.52            # x where the arms meet the ring caps (= inner-hole edge)

# --- slotted coupler element on each arm (rect frame + septum -> 2 windows) ---
box_len_um = 0.892          # x extent of the box
box_height_um = 1.043       # y extent of the box
box_wall_x_um = 0.066       # left/right border thickness (x)
box_wall_y_um = 0.254       # top/bottom border thickness (y)
box_septum_um = 0.114       # central septum thickness (x)

# --- MZI imbalance knob (um): 0.0 = balanced (as drawn). Downstream FSR retarget.
#     Named `delta_length` per the optimize-to-spec parametric contract. ---
delta_length = 0.0

# ================= derived layout =================
cx = device_length_um / 2.0
cy = device_width_um / 2.0
y_up = cy + arm_sep_um / 2.0            # upper arm centerline
y_dn = cy - arm_sep_um / 2.0            # lower arm centerline
y_att_up = cy + splitter_gap_um / 2.0  # upper arm attach point at the caps
y_att_dn = cy - splitter_gap_um / 2.0
x_r = device_length_um - port_x_um     # right combine x

# window geometry (derived from the box knobs)
_interior_w = box_len_um - 2 * box_wall_x_um
_win_w = (_interior_w - box_septum_um) / 2.0
_win_h = box_height_um - 2 * box_wall_y_um
_win_off = (box_septum_um + _win_w) / 2.0  # window center offset from box center


def _polyline_length(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def _filled_rrect(a, b, rx, ry):
    """Filled rounded rectangle (half-extents a,b; corner radii rx,ry), centered."""
    c = gf.Component()
    c << gf.components.rectangle(size=(2 * a, 2 * (b - ry)), layer=LAYER, centered=True)
    c << gf.components.rectangle(size=(2 * (a - rx), 2 * b), layer=LAYER, centered=True)
    for sx in (-1, 1):
        for sy in (-1, 1):
            e = c << gf.components.ellipse(radii=(rx, ry), layer=LAYER)
            e.move((sx * (a - rx), sy * (b - ry)))
    return c


def _upper_arm_points():
    return [
        (port_x_um, y_att_up),
        (port_x_um + splitter_len_um, y_up),
        (x_r - splitter_len_um, y_up),
        (x_r, y_att_up),
    ]


def _lower_arm_points():
    pts = [
        (port_x_um, y_att_dn),
        (port_x_um + splitter_len_um, y_dn),
    ]
    if delta_length > 1e-6:
        # downward pocket in the clear corridor between the splitter fan and the
        # box (x in ~[0.52, 1.05]): the two vertical legs add 2*depth = delta_length
        # of centerline length and ~arm_width*delta of area, without shifting
        # anything downstream. (Downstream FSR retuning reshapes with more room.)
        xp, wd = 0.79, 0.08
        depth = delta_length / 2.0
        pts += [(xp, y_dn), (xp, y_dn - depth), (xp + wd, y_dn - depth), (xp + wd, y_dn)]
    pts += [
        (x_r - splitter_len_um, y_dn),
        (x_r, y_att_dn),
    ]
    return pts


def build():
    mat = gf.Component()  # all positive material

    # --- outer racetrack ring: outer rounded rect minus inner-hole rounded rect ---
    outer = _filled_rrect(device_length_um / 2.0, device_width_um / 2.0,
                          ring_outer_rx_um, ring_outer_ry_um)
    hole = _filled_rrect(ring_hole_halfx_um, ring_hole_halfy_um,
                         ring_inner_rx_um, ring_inner_ry_um)
    ring = gf.boolean(outer, hole, operation="not", layer=LAYER)
    ring_ref = mat << ring
    ring_ref.move((cx, cy))

    # --- MZI arms (real gf.Path objects; lengths measured from their points) ---
    up_pts = _upper_arm_points()
    dn_pts = _lower_arm_points()
    mat << gf.path.extrude(gf.Path(up_pts), width=arm_width_um, layer=LAYER)
    mat << gf.path.extrude(gf.Path(dn_pts), width=arm_width_um, layer=LAYER)

    # --- box bodies (positive) for each arm ---
    for yc in (y_up, y_dn):
        body = gf.components.rectangle(size=(box_len_um, box_height_um),
                                       layer=LAYER, centered=True)
        (mat << body).move((cx, yc))

    # --- windows (subtracted from everything so arm material never fills them) ---
    holes = gf.Component()
    for yc in (y_up, y_dn):
        for sign in (-1, 1):
            w = gf.components.rectangle(size=(_win_w, _win_h), layer=LAYER, centered=True)
            (holes << w).move((cx + sign * _win_off, yc))

    final = gf.boolean(mat, holes, operation="not", layer=LAYER)

    # --- lengths.json (arm centerlines from the path point lists) ---
    arms = {"top": _polyline_length(up_pts), "bot": _polyline_length(dn_pts)}
    payload = {"arms": arms, "delta_length_um": abs(arms["top"] - arms["bot"])}
    (FsPath(__file__).parent / "lengths.json").write_text(json.dumps(payload, indent=2))

    return final


if __name__ == "__main__":
    comp = build()
    out = FsPath(__file__).parent / "final7_device.gds"
    comp.write_gds(str(out))
    print(f"wrote {out}")
    print(f"bbox um: {comp.dbbox()}")
