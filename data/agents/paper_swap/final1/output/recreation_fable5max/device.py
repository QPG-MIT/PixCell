"""Adiabatic 1x2 power splitter — primitives-only parametric recreation.

Topology (see recreation_log.json): a central input guide runs a short
lead-in, then linearly tapers down to a truncated tip while two flanking
outer guides taper up from truncated tips at a ~0.1 um edge gap (adiabatic
three-guide transfer region); past the central tip the outer guides S-bend
apart (quintic centerline) into two parallel output ports.

Every polygon comes from a gf.Path centerline extruded on layer (1, 0)
(straight extrusion, linear-width transition, or constant-width S-bend).
No component stencils, no raw polygons, no image reads.

Measurement contract: lengths.json is computed from the Path objects at
build time. arms = the two distinct path systems of the device — the
central transfer path (input -> central tip, length = lead_in_length +
transfer_length) and the outer routing path (S-bend + output straight,
independent of the transfer knob) — so delta_length_um = |L1 - L2| moves
1:1 with transfer_length. Stretching transfer_length stretches all three
tapers: d(area)/d(transfer_length) = mean central taper width + 2 x mean
outer taper width (printed at build time as knob_area_width_um).
"""

import json
from pathlib import Path as FilePath

import numpy as np
import gdsfactory as gf

LAYER = (1, 0)
HERE = FilePath(__file__).resolve().parent

# ----------------------- tunables (um) -----------------------
lead_in_length = 3.05        # straight central input section
transfer_length = 22.01      # adiabatic transfer region length (PRIMARY function knob)
w_in = 0.270                 # central input width
w_center_tip = 0.074         # central taper truncated tip width
y_center = 0.0149            # central guide axis (figure sits slightly high of center)

w_outer_tip_top = 0.068      # outer guide starting tip widths
w_outer_tip_bot = 0.070
y_tip_top = 0.2807           # outer tip centerline offsets at the tip
y_tip_bot = -0.2630
y_sbend_in_top = 0.2768      # outer centerline offsets where the S-bend starts
y_sbend_in_bot = -0.2524
tip_clearance_top = 0.55     # x from central tip to S-bend start
tip_clearance_bot = 0.60
sbend_length_top = 10.55     # S-bend x-extents
sbend_length_bot = 10.75
y_out_top = 0.7279           # output port centerline offsets
y_out_bot = -0.7295
w_out_top = 0.244            # outer guide width from taper end through output
w_out_bot = 0.240
output_straight_top = 3.84   # output straight lengths after the S-bend
output_straight_bot = 3.59
sbend_npoints = 201
# The source figure's stroke rendering fattens the guides where the S-bend
# slope is largest (verified column-wise against the target bitmap); modeled
# as a width bump proportional to the quintic slope shape t^2(1-t)^2.
sbend_bump_top = 0.004
sbend_bump_bot = 0.016
sbend_bump_segments = 6


def _quintic(t: np.ndarray) -> np.ndarray:
    """Smootherstep 0->1 with zero slope and curvature at both ends."""
    return t**3 * (10.0 - 15.0 * t + 6.0 * t**2)


def _sbend_points(x0: float, y0: float, length: float, y1: float) -> np.ndarray:
    t = np.linspace(0.0, 1.0, sbend_npoints)
    xs = x0 + t * length
    ys = y0 + (y1 - y0) * _quintic(t)
    return np.column_stack([xs, ys])


def _slope_shape(t: float) -> float:
    """Quintic slope profile normalized to 1 at mid-bend: t^2(1-t)^2 / (1/16)."""
    return 16.0 * t * t * (1.0 - t) * (1.0 - t)


def _even_grid(w: float) -> float:
    """Widths must sit on the 2-dbu (0.002 um) grid for symmetric extrusion."""
    return round(w * 500.0) / 500.0


def _extrude_band(p: gf.Path, w0: float, w1: float) -> gf.Component:
    """Extrude a centerline with constant or linearly varying width."""
    w0, w1 = _even_grid(w0), _even_grid(w1)
    if abs(w0 - w1) < 1e-9:
        return p.extrude(width=w0, layer=LAYER)
    trans = gf.path.transition(
        gf.cross_section.cross_section(width=w0, layer=LAYER),
        gf.cross_section.cross_section(width=w1, layer=LAYER),
        width_type="linear",
    )
    return gf.path.extrude_transition(p, trans)


@gf.cell
def adiabatic_splitter_1x2() -> gf.Component:
    c = gf.Component()

    x_tip = lead_in_length + transfer_length  # central tip x

    # central guide: lead-in + down-taper
    p_lead = gf.Path(np.array([[0.0, y_center], [lead_in_length, y_center]]))
    p_ctaper = gf.Path(np.array([[lead_in_length, y_center], [x_tip, y_center]]))
    c.add_ref(_extrude_band(p_lead, w_in, w_in))
    c.add_ref(_extrude_band(p_ctaper, w_in, w_center_tip))

    # outer guides: up-taper (tilted) + quintic S-bend + output straight
    arms = {}
    for tag, w_tip, y_tip, y_in, clr, sb_len, y_out, w_out, out_len, bump in (
        ("top", w_outer_tip_top, y_tip_top, y_sbend_in_top, tip_clearance_top,
         sbend_length_top, y_out_top, w_out_top, output_straight_top, sbend_bump_top),
        ("bot", w_outer_tip_bot, y_tip_bot, y_sbend_in_bot, tip_clearance_bot,
         sbend_length_bot, y_out_bot, w_out_bot, output_straight_bot, sbend_bump_bot),
    ):
        x_sb = x_tip + clr
        p_taper = gf.Path(np.array([[lead_in_length, y_tip], [x_sb, y_in]]))
        pts = _sbend_points(x_sb, y_in, sb_len, y_out)
        p_sbend = gf.Path(pts)
        x_end = x_sb + sb_len
        p_out = gf.Path(np.array([[x_end, y_out], [x_end + out_len, y_out]]))
        c.add_ref(_extrude_band(p_taper, w_tip, w_out))
        # bend extruded in sub-segments with piecewise-linear width following
        # the slope-shaped stroke bump of the source rendering
        n_seg = int(sbend_bump_segments)
        idx = np.linspace(0, sbend_npoints - 1, n_seg + 1).round().astype(int)
        t_nodes = idx / (sbend_npoints - 1)
        w_nodes = [w_out + bump * _slope_shape(float(t)) for t in t_nodes]
        for k in range(n_seg):
            seg = gf.Path(pts[idx[k]: idx[k + 1] + 1])
            c.add_ref(_extrude_band(seg, w_nodes[k], w_nodes[k + 1]))
        c.add_ref(_extrude_band(p_out, w_out, w_out))
        arms[tag] = {
            "taper": float(p_taper.length()),
            "sbend": float(p_sbend.length()),
            "output": float(p_out.length()),
        }

    # measurement contract: lengths.json from the Path objects themselves
    central_transfer = float(p_lead.length() + p_ctaper.length())
    routing_top = arms["top"]["sbend"] + arms["top"]["output"]
    lengths = {
        "arms": {
            "central_transfer_path": central_transfer,
            "outer_routing_path_top": routing_top,
        },
        "delta_length_um": abs(central_transfer - routing_top),
        "segments_um": arms,
        "note": (
            "central_transfer_path = input->central tip (= lead_in_length + "
            "transfer_length); outer_routing_path_top = top S-bend arc + output "
            "straight, which does not depend on transfer_length — so "
            "delta_length_um responds 1:1 to the transfer_length knob. "
            "All values computed from gf.Path objects at build time."
        ),
    }
    (HERE / "lengths.json").write_text(json.dumps(lengths, indent=2))
    return c


if __name__ == "__main__":
    component = adiabatic_splitter_1x2()
    knob_area_width = (
        (w_in + w_center_tip) / 2
        + (w_outer_tip_top + w_out_top) / 2
        + (w_outer_tip_bot + w_out_bot) / 2
    )
    print(f"bbox: {component.bbox_np().tolist()}")
    print(f"knob_area_width_um (for verify_knob_response width_um): {knob_area_width:.4f}")
    # with_metadata=False: kfactory's $$$CONTEXT_INFO$$$ metadata cell references
    # every cell, which breaks naive gdstk top_level() area measurement.
    component.write_gds(HERE / "adiabatic_splitter_1x2.gds", with_metadata=False)
