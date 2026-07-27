"""
Recreation of experiments/catalog_swap/cat1/device_bw.png

Device: UNBALANCED MACH-ZEHNDER INTERFEROMETER (MZI)
  input taper -> 1x2 MMI splitter -> two stadium/racetrack arms (unequal height,
  giving a path-length difference delta_length) -> 2x1 MMI combiner -> output taper.

Primitives only: gf.Path + extrude (arms), rectangle (MMI), taper, straight.
No gf.components device stencils (no mmi1x2/coupler/ring). Layer (1,0). GDSFactory 9.20.7.

Coordinate frame: device axis (input/output bus) at y = 0, x increases left->right.
"""
import json
from pathlib import Path

import numpy as np
import gdsfactory as gf

# ============================================================================
# TOP-LEVEL TUNABLES  (JEE-substitutable `name = value`)
# The FUNCTION knobs of an unbalanced MZI are all here.
# ============================================================================
LAYER = (1, 0)

# --- interferometer path-length difference (the FSR knob) -------------------
delta_length = 10.12          # um  arm optical path-length difference (sets FSR)

# --- waveguide / arm geometry ----------------------------------------------
wg_width = 0.54               # um  routing waveguide width in the arms
stadium_width = 20.08         # um  separation of the two vertical arm sides (centre-to-centre)
corner_radius = 7.45
base_arm_straight = 6.19
approach_dx = 19.96           # um  horizontal run from MMI output to the vertical side
approach_dy = 8.125           # um  vertical rise (bus offset + this = vertical-side start y)
bez_t = 18.5
bez_u = 7.8
bez_v = 1.5

# --- 1x2 / 2x1 MMI couplers -------------------------------------------------
mmi_width = 2.56              # um  MMI multimode-region width (governs the split)
mmi_length = 5.51             # um  MMI length (governs 50/50 balance)
mmi_out_offset = 0.625        # um  half center-to-center of the two MMI outputs
mmi_out_width = 0.97          # um  waveguide width at the MMI ports (arms taper from this)
taper_frac = 0.32

# --- access tapers / ports --------------------------------------------------
mmi_taper_length = 8.30       # um  input/output access-taper length
mmi_taper_width = 0.97        # um  taper wide end (feeds the MMI)
port_tip_width = 0.50         # um  input/output waveguide tip width

# --- fixed layout anchors (from calibrated image, um) -----------------------
DEVICE_LENGTH = 91.10         # um  full footprint length
LEFT_MMI_X0 = 10.01           # um  left edge of the splitter MMI
# ============================================================================


def _bezier(p0, p1, p2, p3, s, n):
    out = []
    for i in range(0, n + 1):
        t = i / n
        mt = 1 - t
        x = mt**3 * p0[0] + 3 * mt**2 * t * p1[0] + 3 * mt * t**2 * p2[0] + t**3 * p3[0]
        y = mt**3 * p0[1] + 3 * mt**2 * t * p1[1] + 3 * mt * t**2 * p2[1] + t**3 * p3[1]
        out.append((x, s * y))
    return out


def _arm_paths(straight_len: float, up: bool, n: int = 80):
    """Rounded-rectangle (stadium) arm as THREE centreline sub-paths.

    approach : MMI output -> vertical side (tapers mmi_out_width -> wg_width)
    cap      : vertical -> quarter-circle corner -> flat top -> corner -> vertical
    exit     : vertical side -> combiner input (tapers wg_width -> mmi_out_width)

    `up=True` bulges above the bus, else below. Only `straight_len` differs
    between the two arms -> the path-length difference (delta_length knob),
    and it lives entirely in the constant-width cap piece.
    """
    s = 1.0 if up else -1.0
    yo = mmi_out_offset
    Rc = corner_radius
    x_vert = approach_dx
    y_v = yo + approach_dy
    x_vert2 = x_vert + stadium_width
    x_end = x_vert2 + approach_dx

    approach = _bezier((0.0, yo), (bez_t, yo), (x_vert - bez_v, y_v - bez_u), (x_vert, y_v), s, n)

    y_top = y_v + straight_len
    cap = [(x_vert, s * y_v), (x_vert, s * y_top)]
    for i in range(1, n + 1):                      # top-left corner
        th = np.pi - (np.pi / 2) * (i / n)
        cap.append(((x_vert + Rc) + Rc * np.cos(th), s * (y_top + Rc * np.sin(th))))
    y_cap = y_top + Rc
    x_right_corner = x_vert + stadium_width - Rc
    cap.append((x_right_corner, s * y_cap))        # flat top
    for i in range(1, n + 1):                       # top-right corner
        th = (np.pi / 2) * (1 - i / n)
        cap.append((x_right_corner + Rc * np.cos(th), s * (y_top + Rc * np.sin(th))))
    cap.append((x_vert2, s * y_v))                  # vertical down

    exit_ = _bezier((x_vert2, y_v), (x_vert2 + bez_v, y_v - bez_u), (x_end - bez_t, yo), (x_end, yo), s, n)

    return (gf.Path(np.array(approach)), gf.Path(np.array(cap)), gf.Path(np.array(exit_)))


def _taper_early(frac):
    """Linear taper w1->w2 completing within the first `frac` of the path."""
    def wfun(t, w1, w2):
        tt = np.clip(np.asarray(t) / frac, 0.0, 1.0)
        return w1 + (w2 - w1) * tt
    return wfun


def _taper_late(frac):
    """Linear taper w1->w2 held at w1 until (1-frac), then ramping to w2."""
    def wfun(t, w1, w2):
        tt = np.clip((np.asarray(t) - (1.0 - frac)) / frac, 0.0, 1.0)
        return w1 + (w2 - w1) * tt
    return wfun


@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    xs_wide = gf.cross_section.cross_section(width=mmi_out_width, layer=LAYER)
    xs_narrow = gf.cross_section.cross_section(width=wg_width, layer=LAYER)
    trans_in = gf.path.transition(xs_wide, xs_narrow, width_type=_taper_early(taper_frac))
    trans_out = gf.path.transition(xs_narrow, xs_wide, width_type=_taper_late(taper_frac))

    top_straight = base_arm_straight
    bot_straight = base_arm_straight + delta_length / 2.0

    left_mmi_x1 = LEFT_MMI_X0 + mmi_length          # right edge of splitter
    right_mmi_x0 = DEVICE_LENGTH - left_mmi_x1       # left edge of combiner (mirror)

    # ---- two MZI arms (stadium arches) ------------------------------------
    # approach & exit taper mmi_out_width <-> wg_width; the cap is wg_width.
    arm_lengths = {}
    for name, straight, up in (("top", top_straight, True), ("bottom", bot_straight, False)):
        approach, cap, exit_ = _arm_paths(straight, up=up)
        refs = [
            c << gf.path.extrude_transition(approach, trans_in),
            c << cap.extrude(xs_narrow),
            c << gf.path.extrude_transition(exit_, trans_out),
        ]
        for ref in refs:
            ref.move((left_mmi_x1, 0.0))   # start arm at splitter output port
        arm_lengths[name] = float(approach.length() + cap.length() + exit_.length())

    # ---- 1x2 splitter and 2x1 combiner MMIs (solid rectangles) ------------
    for mmi_x0 in (LEFT_MMI_X0, right_mmi_x0):
        mmi = c << gf.components.rectangle(size=(mmi_length, mmi_width),
                                           layer=LAYER, centered=False)
        mmi.move((mmi_x0, -mmi_width / 2.0))

    # ---- input / output access tapers + straights -------------------------
    # input: tip (port_tip_width) -> mmi_taper_width over mmi_taper_length,
    # then a short straight up to the MMI entrance.
    in_gap = LEFT_MMI_X0 - mmi_taper_length          # 0.97um straight to MMI
    in_taper = c << gf.components.taper(length=mmi_taper_length,
                                        width1=port_tip_width,
                                        width2=mmi_taper_width, layer=LAYER)
    in_taper.move((0.0, 0.0))                          # tip at x=0, centred on y=0
    if in_gap > 0:
        s = c << gf.path.straight(length=in_gap).extrude(width=mmi_taper_width, layer=LAYER)
        s.move((mmi_taper_length, 0.0))
    # output (mirror of input about device centre)
    out_taper = c << gf.components.taper(length=mmi_taper_length,
                                         width1=port_tip_width,
                                         width2=mmi_taper_width, layer=LAYER)
    out_taper.mirror_x(x=0)
    out_taper.move((DEVICE_LENGTH, 0.0))
    if in_gap > 0:
        s2 = c << gf.path.straight(length=in_gap).extrude(width=mmi_taper_width, layer=LAYER)
        s2.move((DEVICE_LENGTH - mmi_taper_length - in_gap, 0.0))

    # ---- write lengths.json (arm centreline lengths from the Paths) -------
    lengths = {
        "arms": {"top": arm_lengths["top"], "bottom": arm_lengths["bottom"]},
        "delta_length_um": abs(arm_lengths["bottom"] - arm_lengths["top"]),
    }
    out_dir = Path(__file__).parent
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))

    return c


if __name__ == "__main__":
    comp = device().copy()
    comp.flatten()   # keep the device a clean top-level cell (not nested under kfactory metadata)
    gds_path = Path(__file__).parent / "device.gds"
    comp.write_gds(str(gds_path))
    print("wrote", gds_path)
