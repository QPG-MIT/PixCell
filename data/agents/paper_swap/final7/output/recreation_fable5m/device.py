"""Stadium-loop resonator with slot-loaded twin-arm bridge (paper_swap/final7).

Primitives-only parametric recreation: every shape is a gf.components.rectangle
placed from top-level tunables. The ring boundaries are generalized
superellipses (the calibration is anisotropic, so pixel-space round caps are
elliptical in the calibrated um frame) emitted as thin rectangle slabs.

Coordinate frame: calibrated absolute um, x in [0, DEV_L], y in [0, DEV_H].
Layer (1, 0). gdsfactory 9.20.7.
"""

import numpy as np
import gdsfactory as gf

LAYER = (1, 0)

# ---------------- tunables (um, calibrated frame) ----------------
DEV_L = 3.0                 # device extent along x (footprint length)
DEV_H = 5.5                 # device extent along y (footprint width)

# outer ring boundary: generalized superellipse |dx/A|^px + |dy/B|^py = 1
ring_outer_ax = 1.5033      # semi-axis along x
ring_outer_ay = 2.759      # semi-axis along y
ring_outer_px = 4.041       # x exponent (squareness of caps)
ring_outer_py = 1.8852      # y exponent

# inner ring boundary (clear opening of the loop)
ring_inner_ax = 1.2354
ring_inner_ay = 2.234
ring_inner_px = 4.5834
ring_inner_py = 1.6443

# trunk: block joining the side wall to the Y-branch tips
tip_x_um = 0.5203           # x of the trunk tip (from device left edge)
trunk_left_x = 0.27         # trunk left edge (overlaps the ring wall; union)
trunk_half_h = 0.6558       # trunk half-height about the midline

# bridge arms (each of the four diagonal+horizontal bands)
arm_width_um = 0.4302       # arm width (vertical, in the horizontal section)
arm_center_y = 0.9201       # center height of horizontal arm section above midline
arm_slope = 2.1873          # dy/dx of the diagonal section (um frame)
arm_kink_top_x = 0.7041     # x where the top edge of the upper-left arm kinks
arm_kink_bot_x = 0.7428     # x where the bottom edge kinks

# slotted boxes (capacitive loading elements)
box_left_x = 1.0522         # box left edge
box_width = 0.8917          # box outer width
box_center_y = 0.9096       # box center height above midline
box_height = 1.0437         # box outer height
box_wall_x = 0.0650         # side wall thickness (x)
box_wall_y = 0.2504         # top/bottom wall thickness (y)
box_bar_width = 0.1122      # central bar width (x)
window_height = 0.5430      # clear window height (y)

# path-length imbalance knob (um): a detour stub grown from the upper box's
# bottom wall into the central clear hexagon; lengthens the upper bridge path
# by exactly delta_length relative to the lower one. 0 = symmetric (the image).
delta_length = 0.0
stub_width = 1.0            # detour stub width (x)

# discretization (raster is 517 x 141.8 px/um; slabs ~2 px)
n_ring_slabs = 600
n_arm_strips = 140


def _rect(c, x0, y0, x1, y1):
    if x1 - x0 <= 1e-6 or y1 - y0 <= 1e-6:
        return
    r = c.add_ref(gf.components.rectangle(size=(x1 - x0, y1 - y0), layer=LAYER))
    r.move((x0, y0))


def _half_width(dy, a, b, p_x, p_y):
    """dx of a generalized superellipse at height dy from center."""
    t = (abs(dy) / b) ** p_y
    if t >= 1.0:
        return 0.0
    return a * (1.0 - t) ** (1.0 / p_x)


@gf.cell
def stadium_bridge_resonator() -> gf.Component:
    c = gf.Component()
    xc, yc = DEV_L / 2, DEV_H / 2

    # ---- ring: outer superellipse minus inner superellipse, as y-slabs ----
    edges = np.linspace(yc - ring_outer_ay, yc + ring_outer_ay, n_ring_slabs + 1)
    for y0, y1 in zip(edges[:-1], edges[1:]):
        ym = (y0 + y1) / 2
        xo = _half_width(ym - yc, ring_outer_ax, ring_outer_ay,
                         ring_outer_px, ring_outer_py)
        if xo <= 0:
            continue
        xi = _half_width(ym - yc, ring_inner_ax, ring_inner_ay,
                         ring_inner_px, ring_inner_py)
        if xi > 0:
            _rect(c, xc - xo, y0, xc - xi, y1)
            _rect(c, xc + xi, y0, xc + xo, y1)
        else:
            _rect(c, xc - xo, y0, xc + xo, y1)

    # ---- interior: build upper-left quadrant pieces, mirror to the rest ----
    def mirrored(x0, y0, x1, y1):
        """Emit a rect in all four mirror images (dedup handled by geometry)."""
        for sx in (0, 1):
            for sy in (0, 1):
                a0, a1 = (x0, x1) if sx == 0 else (2 * xc - x1, 2 * xc - x0)
                b0, b1 = (y0, y1) if sy == 0 else (2 * yc - y1, 2 * yc - y0)
                _rect(c, a0, b0, a1, b1)

    # trunk (emit left+right via x-mirror only; spans midline symmetric in y)
    for sx in (0, 1):
        x0, x1 = (trunk_left_x, tip_x_um) if sx == 0 else \
                 (2 * xc - tip_x_um, 2 * xc - trunk_left_x)
        _rect(c, x0, yc - trunk_half_h, x1, yc + trunk_half_h)

    # arm: horizontal section (upper-left; mirrored to all quadrants)
    y_top = yc + arm_center_y + arm_width_um / 2
    y_bot = yc + arm_center_y - arm_width_um / 2
    mirrored(arm_kink_bot_x, y_bot, box_left_x + box_wall_x, y_top)

    # arm: diagonal section as x-strips from the trunk tip to the kinks
    xs = np.linspace(tip_x_um, arm_kink_bot_x, n_arm_strips + 1)
    for x0, x1 in zip(xs[:-1], xs[1:]):
        xm = (x0 + x1) / 2
        yt = y_top - arm_slope * max(0.0, arm_kink_top_x - xm)
        yb = y_bot - arm_slope * max(0.0, arm_kink_bot_x - xm)
        yb = max(yb, yc)          # never cross the midline (trunk covers there)
        if yt > yb:
            mirrored(x0, yb, x1, yt)

    # slotted box (upper; mirrored in y for the lower one)
    bx0 = box_left_x
    bx1 = box_left_x + box_width
    by0 = yc + box_center_y - box_height / 2
    by1 = yc + box_center_y + box_height / 2
    bar0 = xc - box_bar_width / 2
    bar1 = xc + box_bar_width / 2
    for sy in (0, 1):
        def Y(v, sy=sy):
            return v if sy == 0 else 2 * yc - v
        yA, yB = sorted((Y(by0), Y(by1)))
        # top + bottom walls
        _rect(c, bx0, yA, bx1, yA + box_wall_y)
        _rect(c, bx0, yB - box_wall_y, bx1, yB)
        # side walls + central bar (full box height; overlap is fine)
        _rect(c, bx0, yA, bx0 + box_wall_x, yB)
        _rect(c, bx1 - box_wall_x, yA, bx1, yB)
        _rect(c, bar0, yA, bar1, yB)

    # detour stub for delta_length (upper bridge only; solid block hanging
    # from the upper box's bottom wall into the clear central hexagon)
    if delta_length > 1e-9:
        h_d = delta_length / 2                      # centerline detour depth
        arm_cy = yc + arm_center_y
        stub_top = yc + box_center_y - box_height / 2   # upper box bottom edge
        stub_bot = arm_cy - h_d - arm_width_um / 2      # detour cap bottom
        _rect(c, xc - stub_width / 2, stub_bot, xc + stub_width / 2, stub_top)

    return c


def bridge_paths() -> dict[str, gf.Path]:
    """Centerline gf.Path of each bridge arm (upper carries the detour)."""
    xc, yc = DEV_L / 2, DEV_H / 2
    arm_cy = arm_center_y
    x_end = box_left_x + box_width

    def one(sign: int, detour: float) -> gf.Path:
        pts = [(tip_x_um, yc), (arm_kink_bot_x, yc + sign * arm_cy)]
        if detour > 1e-9:
            h_d = detour / 2
            pts += [
                (xc - stub_width / 4, yc + sign * arm_cy),
                (xc - stub_width / 4, yc + sign * (arm_cy - h_d)),
                (xc + stub_width / 4, yc + sign * (arm_cy - h_d)),
                (xc + stub_width / 4, yc + sign * arm_cy),
            ]
        pts += [
            (x_end, yc + sign * arm_cy),
            (2 * xc - arm_kink_bot_x, yc + sign * arm_cy),
            (2 * xc - tip_x_um, yc),
        ]
        return gf.Path(np.array(pts))

    return {"upper_bridge": one(+1, delta_length), "lower_bridge": one(-1, 0.0)}


def write_lengths(path: str = "lengths.json") -> dict:
    import json
    paths = bridge_paths()
    arms = {name: float(p.length()) for name, p in paths.items()}
    vals = list(arms.values())
    payload = {"arms": arms, "delta_length_um": abs(vals[0] - vals[1])}
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return payload


if __name__ == "__main__":
    component = stadium_bridge_resonator()
    component.write_gds("device.gds", with_metadata=False)
    lengths = write_lengths()
    print("wrote device.gds", component.bbox_np())
    print("lengths.json", lengths)
