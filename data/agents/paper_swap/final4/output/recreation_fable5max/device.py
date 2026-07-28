"""Symmetric directional coupler recreated from data/agents/paper_swap/final4/device_bw.png.

Two identical waveguides, mirrored about the horizontal midline: straight lead
-> two-arc S-bend in (port-side radius bend_radius_in, then coupling-side
radius bend_radius_out) -> parallel coupling section -> mirrored two-arc S-bend
out -> straight lead. The arc segments carry a linear width taper from
wg_width at their flat-tangent ends to sbend_mid_width at the max-slope joint,
matching the slope-dependent stroke widening of the source rendering; leads and
the coupling section are constant wg_width, so the coupling gap is set by
wg_width alone. Primitives only (gf.path straight/arc composition + extrude
with taper, @gf.cell assembly); layer (1, 0); gdsfactory 9.20.7.

The S-bend angle is derived from the radii and the lateral offset the arms
must close, so retuning coupling_gap / io_separation keeps the geometry
consistent. lengths.json is recomputed from the built paths on every run
(never hand-entered) and follows the two-arm contract of
homi.spec_optimization: delta_length_um is the arm-length difference, which is
0 by symmetry for this coupler. The coupler's own function-knob readback is
coupling_section_measured_um — the geometry-measured length of the central
minimum-separation section.
"""

import json
from pathlib import Path

import numpy as np
import gdsfactory as gf

# Function-defining tunables (um). Keep each line a bare `name = value`
# assignment: JEE and homi.spec_optimization substitute them textually.
wg_width = 0.656
coupling_gap = 0.296
coupling_length = 1.090
io_separation = 2.344
straight_in = 0.865
bend_radius_in = 15.781
bend_radius_out = 25.959
sbend_mid_width = 0.670

LAYER = (1, 0)
ARC_NPOINTS = 400


def _sbend_angle_deg() -> float:
    """Arc angle closing each arm's lateral offset with the two tangent arcs."""
    dy_arm = (io_separation - (coupling_gap + wg_width)) / 2.0
    c = 1.0 - dy_arm / (bend_radius_in + bend_radius_out)
    return float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0))))


def _arm_segments() -> list[tuple[np.ndarray, float, float]]:
    """Top-arm centerline segments as (points, start_width, end_width).

    Exact analytic construction: straight lead, port-side arc (R_in) to the
    max-slope joint, coupling-side arc (R_out) onto the plateau, the coupling
    straight, then the x-mirrored arcs and lead for the right half.
    """
    w, wm = wg_width, sbend_mid_width
    theta = np.radians(_sbend_angle_deg())
    y_port = io_separation / 2.0
    y_couple = (coupling_gap + wg_width) / 2.0
    r_in, r_out = bend_radius_in, bend_radius_out

    lead_l = np.array([[0.0, y_port], [straight_in, y_port]])

    phi1 = np.linspace(np.pi / 2, np.pi / 2 - theta, ARC_NPOINTS)
    c1 = np.array([straight_in, y_port - r_in])
    arc1_l = c1 + r_in * np.column_stack([np.cos(phi1), np.sin(phi1)])

    p2 = arc1_l[-1]
    c2 = p2 + r_out * np.array([np.sin(theta), np.cos(theta)])
    phi2 = np.linspace(1.5 * np.pi - theta, 1.5 * np.pi, ARC_NPOINTS)
    arc2_l = c2 + r_out * np.column_stack([np.cos(phi2), np.sin(phi2)])

    p3 = arc2_l[-1]
    plateau = np.array([[p3[0], y_couple], [p3[0] + coupling_length, y_couple]])

    x_mid = p3[0] + coupling_length / 2.0
    mirror = np.array([2.0 * x_mid, 0.0])
    flip = np.array([-1.0, 1.0])
    arc2_r = (mirror + arc2_l[::-1] * flip)
    arc1_r = (mirror + arc1_l[::-1] * flip)
    lead_r = (mirror + lead_l[::-1] * flip)

    return [
        (lead_l, w, w),
        (arc1_l, w, wm),
        (arc2_l, wm, w),
        (plateau, w, w),
        (arc2_r, w, wm),
        (arc1_r, wm, w),
        (lead_r, w, w),
    ]


def _top_arm_points() -> np.ndarray:
    """Full top-arm centerline (joint-deduplicated) for measurement."""
    parts = [seg for seg, _, _ in _arm_segments()]
    pts = [parts[0]]
    for seg in parts[1:]:
        pts.append(seg[1:] if np.allclose(seg[0], pts[-1][-1], atol=1e-9) else seg)
    return np.vstack(pts)


@gf.cell
def directional_coupler() -> gf.Component:
    c = gf.Component()
    for sign in (+1.0, -1.0):
        for seg, w1, w2 in _arm_segments():
            arm_seg = seg * np.array([1.0, sign])
            if w1 == w2:
                c.add_ref(gf.path.extrude(gf.Path(arm_seg), layer=LAYER, width=w1))
            else:
                trans = gf.path.transition(
                    gf.cross_section.cross_section(width=w1, layer=LAYER),
                    gf.cross_section.cross_section(width=w2, layer=LAYER),
                    width_type="linear",
                )
                c.add_ref(gf.path.extrude_transition(gf.Path(arm_seg), trans))
    return c


def _measured_lengths() -> dict:
    """Compute arm lengths and the central minimum-separation span from geometry."""
    pts = _top_arm_points()
    xs, ys = pts[:, 0], pts[:, 1]
    sep = 2.0 * ys  # bottom arm is the exact y-mirror
    min_sep = float(sep.min())
    flat = sep <= min_sep + 1e-3
    coupling_measured = float(xs[flat].max() - xs[flat].min())
    arm_length = float(gf.Path(pts).length())
    return {
        "arms": {"top": arm_length, "bottom": arm_length},
        "delta_length_um": 0.0,
        "coupling_section_measured_um": coupling_measured,
        "min_center_separation_um": min_sep,
        "arm_length_difference_um": 0.0,
        "sbend_angle_deg": _sbend_angle_deg(),
        "device_length_um": float(xs.max() - xs.min()),
    }


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    component = directional_coupler()
    gds_path = out_dir / "device.gds"
    # No kfactory $$$CONTEXT_INFO$$$ cell: it would reference the device cell,
    # demoting it from top level and hiding it from top-cell area measurement.
    component.write_gds(gds_path, with_metadata=False)
    lengths = _measured_lengths()
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    print(f"wrote {gds_path}")
    print(json.dumps(lengths, indent=2))
