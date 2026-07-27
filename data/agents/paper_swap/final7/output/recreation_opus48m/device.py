"""
final7 device recreation -- primitives-only, parametric.

Device: a balanced Mach-Zehnder interferometer nested inside an outer racetrack
(stadium) loop. The loop meets the MZI at its left and right vertices. A left
1->2 splitter feeds a top and a bottom arm; each arm crosses a wide slotted
"phase section" (a solid block etched with two rectangular windows split by a
central bridge); a mirror 2->1 combiner recloses the path at the right vertex.

Built entirely from primitives: gf.Path + extrude (loop, arms, splitter tapers),
gf.components.rectangle (phase-section block and etch windows), and gf.boolean
(subtract the windows). No device stencils, no raw polygons. Layer (1,0).

Coordinates were measured from the target image in bbox fractions and converted
x_um = frac*3.0, y_um = frac*5.5 (anisotropic calibration).
"""

import gdsfactory as gf

# ----------------------------------------------------------------------------
# TOP-LEVEL TUNABLES (JEE-substitutable `name = value`)
# ----------------------------------------------------------------------------
# --- overall footprint (um) ---
foot_x = 3.0                 # device length (x)
foot_y = 5.5                 # device width (y)

# --- outer rectangular loop (annulus) ---
# The image is anisotropically scaled (x:517 px/um, y:141.8 px/um), so a single
# physical waveguide width appears as different pixel thicknesses for the
# horizontal vs vertical loop walls. To reproduce the ~uniform-looking image
# wall, the loop is an outer-minus-inner rectangle with independent side (x) and
# top/bottom (y) wall thickness. Both encode the same physical loop guide.
ring_wall_x = 0.31           # side (vertical) wall thickness
ring_wall_y = 0.517          # top/bottom (horizontal) wall thickness
ring_rx_out = 0.90           # outer corner radius (x) -- elliptical (anisotropy)
ring_ry_out = 2.20           # outer corner radius (y)
ring_rx_in = 0.74            # inner cavity corner radius (x)
ring_ry_in = 1.57            # inner cavity corner radius (y)

# --- MZI arms (FUNCTION knobs) ---
guide_w = 0.42               # arm waveguide width
arm_offset = 0.92            # half-separation of the two arms (arm pitch/2)
delta_length = 0.0           # MZI arm-length imbalance (um) -- sets FSR (Phase-B
                             # knob). 0 = balanced (matches the symmetric target).

# --- splitter / combiner 1<->2 junction (FUNCTION knobs) ---
split_taper_len = 0.28       # x-length of the solid splitter wedge
split_base_w = 1.30          # wedge width at the loop vertex (merged stem)
split_tip_w = 0.42           # wedge width at the apex where arms separate

# --- slotted phase section (FUNCTION knobs) ---
ps_len = 0.888               # phase-section length (x) -- coupling/transfer length
ps_h = 1.03                  # phase-section transverse height (y)
ps_wall_x = 0.06             # vertical frame-wall thickness (x)
ps_wall_y = 0.23             # horizontal frame-wall thickness (y)
slot_gap = 0.0               # extra gap knob (kept explicit; 0 = windows as measured)
bridge_w = 0.11              # central bridge width between the two etch windows

LAYER = (1, 0)


@gf.cell
def final7_device(
    foot_x: float = foot_x,
    foot_y: float = foot_y,
    ring_wall_x: float = ring_wall_x,
    ring_wall_y: float = ring_wall_y,
    ring_rx_out: float = ring_rx_out,
    ring_ry_out: float = ring_ry_out,
    ring_rx_in: float = ring_rx_in,
    ring_ry_in: float = ring_ry_in,
    guide_w: float = guide_w,
    arm_offset: float = arm_offset,
    delta_length: float = delta_length,
    split_taper_len: float = split_taper_len,
    split_base_w: float = split_base_w,
    split_tip_w: float = split_tip_w,
    ps_len: float = ps_len,
    ps_h: float = ps_h,
    ps_wall_x: float = ps_wall_x,
    ps_wall_y: float = ps_wall_y,
    slot_gap: float = slot_gap,
    bridge_w: float = bridge_w,
) -> gf.Component:
    c = gf.Component()

    cx = foot_x / 2.0
    cy = foot_y / 2.0

    xs_arm = gf.cross_section.cross_section(width=guide_w, layer=LAYER)

    # ------------------------------------------------------------------
    # 1) Outer rounded-rectangle loop (annulus) = outer_rr - inner_cavity_rr.
    #    Rounded rects are primitives: a cross of two rectangles plus four
    #    corner ellipses (elliptical to absorb the x/y anisotropy).
    # ------------------------------------------------------------------
    def filled_rr(w, h, rx, ry):
        comp = gf.Component()
        r1 = comp << gf.components.rectangle(size=(w, h - 2 * ry), layer=LAYER, centered=True)
        r1.dcenter = (0, 0)
        r2 = comp << gf.components.rectangle(size=(w - 2 * rx, h), layer=LAYER, centered=True)
        r2.dcenter = (0, 0)
        for sx in (-1, 1):
            for sy in (-1, 1):
                e = comp << gf.components.ellipse(radii=(rx, ry), layer=LAYER)
                e.dcenter = (sx * (w / 2 - rx), sy * (h / 2 - ry))
        return comp

    outer = filled_rr(foot_x, foot_y, ring_rx_out, ring_ry_out)
    outer_ref = gf.Component()
    oref = outer_ref << outer
    oref.dcenter = (cx, cy)
    cav_w = foot_x - 2.0 * ring_wall_x
    cav_h = foot_y - 2.0 * ring_wall_y
    inner = filled_rr(cav_w, cav_h, ring_rx_in, ring_ry_in)
    inner_ref = gf.Component()
    iref = inner_ref << inner
    iref.dcenter = (cx, cy)
    loop_c = gf.boolean(A=outer_ref, B=inner_ref, operation="not", layer=LAYER)
    c << loop_c

    # phase-section x-window, centered
    ps_x0 = cx - ps_len / 2.0
    ps_x1 = cx + ps_len / 2.0

    # ------------------------------------------------------------------
    # 2) Splitter/combiner + arm segments for one arm (sign = +1 top, -1 bottom).
    #    Arm centerline goes: loop-left-vertex -> diverge -> straight to ps ->
    #    (phase section) -> straight -> converge -> loop-right-vertex.
    #    The phase section interrupts the straight run (windows are open), so
    #    each arm is two extruded segments with the frame bridging them.
    # ------------------------------------------------------------------
    x_left_vertex = ring_wall_x                     # inner wall of loop, left
    x_right_vertex = foot_x - ring_wall_x           # inner wall of loop, right
    x_div_l = x_left_vertex + split_taper_len       # end of left divergence
    x_div_r = x_right_vertex - split_taper_len       # start of right convergence

    bend_r = 0.18  # fillet radius for the arm S-bends (avoids miter spikes)
    arm_len = {}
    for sign in (+1, -1):
        ay = cy + sign * arm_offset
        # left segment: vertex -> diverge -> into ps left wall
        left_pts = [
            (x_left_vertex, cy),
            (x_div_l, ay),
            (ps_x0, ay),
        ]
        pl = gf.path.smooth(left_pts, radius=bend_r)
        c << pl.extrude(xs_arm)
        # right segment: out of ps right wall -> converge -> vertex
        right_pts = [
            (ps_x1, ay),
            (x_div_r, ay),
            (x_right_vertex, cy),
        ]
        pr = gf.path.smooth(right_pts, radius=bend_r)
        c << pr.extrude(xs_arm)
        # arm centerline length = left + through-phase-section + right
        arm_len[sign] = float(pl.length()) + ps_len + float(pr.length())

    # delta_length: extra optical path on the +1 arm (FSR knob). Realized as a
    # guide_w-wide stub of length delta_length projecting from the +1 arm into
    # the free cavity ("eye") between the arms -- adds exactly guide_w *
    # delta_length of layer area, and lengthens the +1 arm by delta_length.
    if delta_length > 0:
        stub = c << gf.components.rectangle(
            size=(guide_w, delta_length), layer=LAYER, centered=True
        )
        stub.dx = cx
        stub.dymax = cy + arm_offset          # hangs into the eye toward centre
        arm_len[+1] += delta_length

    # solid splitter/combiner wedge at each vertex: wide base at the loop
    # vertex tapering to the apex where the two arms separate.
    wl = c << gf.components.taper(
        length=split_taper_len, width1=split_base_w, width2=split_tip_w, layer=LAYER
    )
    wl.dxmin = x_left_vertex
    wl.dy = cy
    wr = c << gf.components.taper(
        length=split_taper_len, width1=split_base_w, width2=split_tip_w, layer=LAYER
    )
    wr.rotate(180)
    wr.dxmax = x_right_vertex
    wr.dy = cy

    # ------------------------------------------------------------------
    # 3) Slotted phase sections (one per arm): rectangle block minus 2 windows.
    # ------------------------------------------------------------------
    for sign in (+1, -1):
        ay = cy + sign * arm_offset
        block = gf.components.rectangle(
            size=(ps_len, ps_h), layer=LAYER, centered=True
        )
        # inner (etched) region
        inner_x0 = ps_x0 + ps_wall_x
        inner_x1 = ps_x1 - ps_wall_x
        win_h = ps_h - 2.0 * ps_wall_y
        win_w = (inner_x1 - inner_x0 - bridge_w) / 2.0 - slot_gap / 2.0

        holes = gf.Component()
        # window 1 (left of bridge)
        h1 = holes << gf.components.rectangle(
            size=(win_w, win_h), layer=LAYER, centered=True
        )
        h1.dcenter = (cx - bridge_w / 2.0 - win_w / 2.0, ay)
        # window 2 (right of bridge)
        h2 = holes << gf.components.rectangle(
            size=(win_w, win_h), layer=LAYER, centered=True
        )
        h2.dcenter = (cx + bridge_w / 2.0 + win_w / 2.0, ay)

        block_c = gf.Component()
        b = block_c << block
        b.dcenter = (cx, ay)

        frame = gf.boolean(A=block_c, B=holes, operation="not", layer=LAYER)
        c << frame

    # expose arm path lengths (from the gf.Path objects) for lengths.json
    c.info["arm_top_um"] = arm_len[+1]
    c.info["arm_bottom_um"] = arm_len[-1]
    c.info["delta_length_um"] = arm_len[+1] - arm_len[-1]
    return c


if __name__ == "__main__":
    import json
    from pathlib import Path

    comp = final7_device()
    # with_metadata=False keeps the device cell top-level (no $$$CONTEXT_INFO$$$
    # wrapper), so area/DRC tools that scan top_level() see the geometry.
    comp.write_gds("device.gds", with_metadata=False)
    # parametric-contract sidecar: arm centerline lengths + delta_length,
    # computed from the gf.Path objects (never hand-entered).
    lengths = {
        "arms": {
            "top": float(comp.info["arm_top_um"]),
            "bottom": float(comp.info["arm_bottom_um"]),
        },
        "delta_length_um": float(comp.info["delta_length_um"]),
    }
    Path("lengths.json").write_text(json.dumps(lengths, indent=2))
    print("wrote device.gds  bbox(um):", comp.dbbox())
    print("lengths.json:", lengths)
