"""Rectangular spiral waveguide delay line (cat7) — primitives-only, parametric.

Topology: a single continuous single-mode waveguide wound as nested rounded
rectangles (a concentric inward rectangular spiral). The rounded corners get
LARGER toward the outside (per-loop decreasing radius) so the loops nest
cleanly. After the innermost loop the guide runs an inner return arm — full
width bottom straights joined by a tight central U-turn "hook" that opens
rightward near the center-left.

Built purely from a gf.Path centerline (straights + circular fillet corners,
filleted per-vertex) extruded on a CrossSection. No component stencils, no raw
polygons.

Function-defining knobs are top-level `name = value` tunables (JEE-substitutable).
"""

import numpy as np
import gdsfactory as gf
from gdsfactory.path import smooth, arc

# ---- FUNCTION KNOBS (top-level tunables) --------------------------------
wg_width_um = 0.65          # single-mode waveguide width -> n_eff, loss
pitch_um = 3.00             # center-to-center spacing between adjacent tracks
n_loops = 6                 # wound concentric loops -> total path length (delay)
corner_radius_top_um = 8.0      # TOP corner set-radius (~6um eff)
corner_radius_bot_um = 4.6      # BOTTOM corner set-radius (~4um eff, seam side)
corner_radius_step_um = 0.2      # radius shrink per loop inward
corner_radius_min_um = 3.5
hook_corner_um = 8.0        # bulb-hook corner set-radius (~6um effective)
right_u_radius_um = 1.45    # right-end U-turn (min bend) radius -> bend-loss floor
bulb_top_y_um = 11.8        # apex height of the central ∩ bulb hook
bulb_left_x_um = -68.6      # left wall of the central bulb hook
bulb_right_x_um = -48.5     # right wall of the central bulb hook
inner_right_x_um = 67.0     # right extent of the two inner return straights
outer_half_width_um = 86.42   # outermost track half-extent in x (footprint/2)
outer_half_height_um = 29.42  # outermost track half-extent in y (footprint/2)
lead_in_um = 0.0            # input access-waveguide length -> adds 1:1 to the
                            # optical path length (the delay).  0 keeps the device
                            # inside the footprint; it is the linear delay knob.

LAYER = (1, 0)


def _loop_points(n, pitch, W, H):
    """Concentric inward rectangular spiral (n loops), seam on the bottom-left.

    Returns the centerline points, a per-point corner radius, and the innermost
    (x_seam, r, b) reached.  Insets all four sides by `pitch` per loop.
    """
    l, r, t, b = -W, W, H, -H
    pts = [(l, b)]                       # start bottom-left outer (endpoint, no fillet)
    radii = [0.0]
    for k in range(n):
        Rtop = max(corner_radius_top_um - k * corner_radius_step_um, corner_radius_min_um)
        Rbot = max(corner_radius_bot_um - k * corner_radius_step_um, corner_radius_min_um)
        pts.append((l, t)); radii.append(Rtop)   # top-left corner (x = l)
        pts.append((r, t)); radii.append(Rtop)   # top-right corner
        pts.append((r, b)); radii.append(Rbot)   # bottom-right corner (tight, seam side)
        if k < n - 1:
            pts.append((l + pitch, b)); radii.append(Rbot)  # bottom-left seam corner
            l += pitch
            r -= pitch
            t -= pitch
            b += pitch
        else:
            x_seam = l + pitch
            pts.append((x_seam, b)); radii.append(Rbot)     # innermost loop bottom
    radii[-1] = 0.0                       # last point is an endpoint (no fillet)
    return pts, radii, (l + pitch, r, b)


def _fillet(points, radii, n_arc=64):
    """Round each interior vertex of a polyline with its own circular radius.

    The arc is tangent to both edges at distance r/tan(theta/2) from the vertex
    (theta = interior angle).  Returns a dense (M,2) centerline array.
    """
    pts = np.asarray(points, float)
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        r = radii[i]
        A, V, C = pts[i - 1], pts[i], pts[i + 1]
        u1 = (A - V) / np.linalg.norm(A - V)
        u2 = (C - V) / np.linalg.norm(C - V)
        ang = np.arccos(np.clip(np.dot(u1, u2), -1, 1))    # interior angle
        if r <= 0 or ang < 1e-6 or abs(ang - np.pi) < 1e-6:
            out.append(V)
            continue
        d = r / np.tan(ang / 2.0)                          # tangent setback
        p1 = V + u1 * d
        p2 = V + u2 * d
        bis = u1 + u2
        bis = bis / np.linalg.norm(bis)
        center = V + bis * (r / np.sin(ang / 2.0))
        a1 = np.arctan2(p1[1] - center[1], p1[0] - center[0])
        a2 = np.arctan2(p2[1] - center[1], p2[0] - center[0])
        da = a2 - a1
        while da > np.pi:
            da -= 2 * np.pi
        while da < -np.pi:
            da += 2 * np.pi
        for s in np.linspace(0, 1, n_arc):
            a = a1 + da * s
            out.append(center + r * np.array([np.cos(a), np.sin(a)]))
    out.append(pts[-1])
    return np.asarray(out)


def _inner_arm(b_inner, pitch):
    """Central ∩-bulb hook + two inner return straights joined by a right U.

    The two straights sit one and two pitches above the innermost loop bottom
    (`b_inner`); their left ends feed the tall bulb hook (rounded ∩) at the
    center-left, their right ends are joined by a tight U-turn.
    Returns (bulb_pts, bulb_radii, u_pts).
    """
    y_lower = b_inner + pitch
    y_upper = b_inner + 2 * pitch
    # G-shaped path: upper straight -> up right wall -> over the top ->
    # down left wall -> lower straight (open at the right, closed by the U).
    bulb_pts = [
        (inner_right_x_um, y_upper),
        (bulb_right_x_um, y_upper),
        (bulb_right_x_um, bulb_top_y_um),
        (bulb_left_x_um, bulb_top_y_um),
        (bulb_left_x_um, y_lower),
        (inner_right_x_um, y_lower),
    ]
    bulb_radii = [0.0, hook_corner_um, hook_corner_um,
                  hook_corner_um, hook_corner_um, 0.0]
    # right-end U-turn connecting the two straights
    ymid = 0.5 * (y_upper + y_lower)
    u_pts = [
        (inner_right_x_um, y_upper),
        (inner_right_x_um + right_u_radius_um, ymid),
        (inner_right_x_um, y_lower),
    ]
    return bulb_pts, bulb_radii, u_pts


@gf.cell
def spiral_delay() -> gf.Component:
    loop_pts, loop_radii, (x_seam, r_inner, b_inner) = _loop_points(
        n_loops, pitch_um, outer_half_width_um, outer_half_height_um
    )
    loop_line = _fillet(loop_pts, loop_radii)
    bulb_pts, bulb_radii, u_pts = _inner_arm(b_inner, pitch_um)
    bulb_line = _fillet(bulb_pts, bulb_radii)

    xs = gf.cross_section.cross_section(width=wg_width_um, layer=LAYER)
    c = gf.Component()
    c << gf.Path(loop_line).extrude(xs)
    c << gf.Path(bulb_line).extrude(xs)
    u_path = smooth(points=u_pts, radius=right_u_radius_um, bend=arc)
    c << u_path.extrude(xs)

    if lead_in_um > 0:                       # input access waveguide (outside footprint)
        x0, y0 = loop_pts[0]
        lead = gf.Path([(x0 - lead_in_um, y0), (x0, y0)])
        c << lead.extrude(xs)

    # Delay-line "arms" for the measurement contract:
    #   wound  = the full optical path the light travels through the spiral
    #   straight = the direct port-to-port span it would take without the spiral
    # delta_length_um = the EXCESS optical path (i.e. the delay this device adds).
    wound_um = (
        _path_len(loop_line) + _path_len(bulb_line)
        + _path_len(u_path.points) + lead_in_um
    )
    straight_um = 2.0 * outer_half_width_um   # direct span across the footprint
    delta_len = wound_um - straight_um

    import json as _json
    with open("lengths.json", "w") as _f:
        _json.dump({
            "arms": {"wound_um": wound_um, "straight_reference_um": straight_um},
            "delta_length_um": delta_len,     # excess optical path = the added delay
            "n_loops": n_loops,
            "pitch_um": pitch_um,
        }, _f, indent=2)
    return c


def _path_len(arr):
    d = np.diff(np.asarray(arr, float), axis=0)
    return float(np.hypot(d[:, 0], d[:, 1]).sum())


if __name__ == "__main__":
    c = spiral_delay()
    # flatten into a plain top cell so the geometry is a proper top-level cell
    # (kfactory otherwise wraps it under a $$$CONTEXT_INFO$$$ cell)
    top = gf.Component()
    top.add_ref(c)
    top.flatten()
    top.write_gds("device.gds")
    print("wrote device.gds  bbox(um):", top.bbox_np())
