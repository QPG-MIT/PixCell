"""Spec-driven PDK-swap retune of the recreated MZI -- 220 nm SOI strip.
Phase 6: splitter & combiner upgraded from image-faithful rectangles to properly
dimensioned 1x2 MMIs (symmetric self-imaging), so the bar-port extinction and
insertion loss can actually be met at tier 1. FSR (tier 0) is preserved.

Topology (unchanged MZI): MMI splitter -> {reference arm, delay arm} -> MMI combiner.

Two physics layers:
  * FSR (tier 0): FSR = lambda^2 / (n_g * delta_length). n_g(SOI 220nm/0.5um) ~ 4.06,
    so delta_length = 74.02 um. That much imbalance is folded into a compact
    boustrophedon meander (the long arm); the short arm is a straight reference.
  * Splitter (tier 1): a symmetric-interference 1x2 MMI images the centered input
    into two equal spots. Self-imaging condition (paired/symmetric interference,
    double image): L_mmi = 3 * L_pi / 8, with L_pi = lambda / (2*(n0 - n1)) the beat
    length of the two lowest modes of the W_mmi-wide body (measured with the
    `multimode` evaluator). Output image spots sit at +/- W_mmi/6 from the body
    centerline. By symmetry the split is 50/50 (t=0.5), so ER = -20*log10|2t-1| -> inf
    up to imaging quality; the conductor confirms ER/IL with a tier-1 FDTD.

Primitives only: rectangle (MMI body), taper (access), straight + euler (arms).
No device stencils (no mmi*/coupler*/ring* from gf.components), no raw polygons.
"""

import json
from pathlib import Path

import gdsfactory as gf

# ---------------------------------------------------------------------------
# Tunables (top-level `name = value`, JEE-substitutable). delta_length is the FSR knob;
# mmi_width / mmi_length dimension the self-imaging splitter.
# ---------------------------------------------------------------------------
wg_width = 0.5  # single-mode waveguide width (um) = stack single_mode_width_um
min_feature_um = 0.18  # stack min feature (um); all widths/gaps respect it
delta_length = 74.02  # arm path-length imbalance (um): the FSR knob (== bottom_len - top_len)

# --- 1x2 MMI splitter/combiner (symmetric self-imaging), access tuned for IL (round 2) ---
# Triangulated from 3 measured FDTD points (see phase6_log): capture is set by the output
# mouth APERTURE covering the (inboard, ~+-0.42 um) image spot plus taper adiabaticity, not by
# centering the mouth on the spot. Winning recipe: clean narrow body + WIDE matched mouths parked
# outboard for the DRC gap (aperture still covers the inboard spot) + LONG adiabatic tapers.
mmi_width = (
    2.5  # multimode body width (um); the clean 2-3 mode body -- widening to 3.0 imaged worse
)
mmi_length = 5.500  # body length (um); tier-1 diagnostic fdve-51f6f92e: 2.01 dB/splitter here
# vs 3.52 at 5.700 -- the tier-0 3*L_pi/8=5.700 estimate ran ~4% long (evidence-based correction).
mmi_access_w = 1.0  # MATCHED input & output taper facet width (um): wide aperture covers the image
mmi_taper_len = 11.0  # adiabatic access taper length (um): 0.5<->1.0 over 11 um, slope ~0.045
output_offset = 0.625  # mouth center (um): parked outboard so a 1.0 um mouth clears the DRC gap
# (2*0.625-1.0 = 0.25 um) while its aperture 0.125..1.125 still covers the inboard ~0.42 um spot.

# --- delay arm (meander) ---
meander_fingers = 4  # vertical fingers in the delay arm (structural, fixed)
meander_radius = 3.0  # euler radius (um); re-folded to shrink span for the longer access tapers
io_lead = 2.0  # input/output straight length outside the MMIs (um)

LAYER = (1, 0)
_xs = gf.cross_section.cross_section(width=wg_width, layer=LAYER)


def _mmi_1x2() -> gf.Component:
    """Primitives-only symmetric 1x2 MMI: rectangle body + centered input taper +
    two output access tapers whose wide mouths (mmi_access_w) are parked at +-output_offset.
    Input and output share the same facet mouth width so the image replica of the input field
    is covered by an equal-width output aperture. Ports: 'in' (left), 'out_top'/'out_bot'
    (right, at +-output_offset)."""
    L = mmi_length
    m = gf.Component()
    m.add_ref(gf.components.rectangle(size=(L, mmi_width), layer=LAYER, centered=True))
    tin = m.add_ref(
        gf.components.taper(length=mmi_taper_len, width1=wg_width, width2=mmi_access_w, layer=LAYER)
    )
    tin.move((-L / 2 - mmi_taper_len, 0.0))  # wide mouth meets the body's left edge, centered
    m.add_port(
        "in", center=(-L / 2 - mmi_taper_len, 0.0), width=wg_width, orientation=180, layer=LAYER
    )
    for name, sgn in (("out_top", +1), ("out_bot", -1)):
        to = m.add_ref(
            gf.components.taper(
                length=mmi_taper_len, width1=mmi_access_w, width2=wg_width, layer=LAYER
            )
        )
        to.move((L / 2, sgn * output_offset))  # wide mouth at the image spot on the right facet
        m.add_port(
            name,
            center=(L / 2 + mmi_taper_len, sgn * output_offset),
            width=wg_width,
            orientation=0,
            layer=LAYER,
        )
    return m


def _meander_path(fingers: int, radius: float, finger_height: float) -> gf.Path:
    """Boustrophedon meander: `fingers` vertical straights joined by 180-deg euler
    U-turns. Starts on-axis heading +x and returns to the axis heading +x, so it
    connects splitter->combiner like a straight would -- but longer by the folded detour."""
    p = gf.Path()
    p += gf.path.euler(radius=radius, angle=-90)  # +x -> -y (dip below axis)
    for i in range(fingers):
        p += gf.path.straight(length=finger_height)
        if i < fingers - 1:
            p += gf.path.euler(radius=radius, angle=(180 if i % 2 == 0 else -180))
    p += gf.path.euler(radius=radius, angle=(90 if (fingers - 1) % 2 == 0 else -90))
    return p


# Meander length is exactly affine in finger height: L(Fh) = _span + _g + fingers*Fh.
# Solve finger height so (bottom_len - top_len) == delta_length exactly (top arm = straight _span).
_p1 = _meander_path(meander_fingers, meander_radius, 1.0)
_p2 = _meander_path(meander_fingers, meander_radius, 2.0)
_span = float(_p1.points[-1][0])
_slope = float(_p2.length() - _p1.length())  # == meander_fingers
_g = (float(_p1.length()) - _slope * 1.0) - _span
finger_height = (delta_length - _g) / meander_fingers
assert finger_height >= min_feature_um, (
    f"delta_length={delta_length} too small for {meander_fingers} fingers "
    f"(finger_height={finger_height:.3f} < min_feature {min_feature_um})"
)
# DRC: the two MMI output access mouths (width mmi_access_w at +-output_offset) must not
# crowd below the min gap.
_out_gap = 2.0 * output_offset - mmi_access_w
assert _out_gap >= 0.2, f"MMI output-guide gap {_out_gap:.3f} um < 0.2 um; widen mmi_width"
assert wg_width >= min_feature_um and mmi_access_w >= min_feature_um


@gf.cell
def mzi_soi220() -> gf.Component:
    c = gf.Component()
    mmi = _mmi_1x2()
    half = mmi_length / 2.0 + mmi_taper_len  # cell-local |x| of the outer ports

    # Splitter: place so its single input port sits at (io_lead, 0).
    sp = c.add_ref(mmi)
    sp.move((io_lead + half, 0.0))
    x_a = float(sp.ports["out_top"].center[0])  # arm start x
    off = output_offset  # arm y-offset = MMI output mouth center (+-0.625 um)

    # Delay + reference arms span _span horizontally, at y = +-off.
    top_path = gf.path.straight(length=_span)
    bottom_path = _meander_path(meander_fingers, meander_radius, finger_height)
    top_len = float(top_path.length())
    bottom_len = float(bottom_path.length())
    top_ref = c.add_ref(gf.path.extrude(top_path, cross_section=_xs))
    top_ref.move((x_a, +off))
    bot_ref = c.add_ref(gf.path.extrude(bottom_path, cross_section=_xs))
    bot_ref.move((x_a, -off))

    # Combiner: mirror of the splitter, arm-facing ports landing at x_b = x_a + _span.
    x_b = x_a + _span
    cb = c.add_ref(mmi)
    cb.mirror_x()
    cb.move((x_b + half, 0.0))

    # Input / output single-mode straights.
    in_ref = c.add_ref(gf.path.extrude(gf.path.straight(length=io_lead), cross_section=_xs))
    in_ref.move((0.0, 0.0))
    out_x = float(cb.ports["in"].center[0])
    out_ref = c.add_ref(gf.path.extrude(gf.path.straight(length=io_lead), cross_section=_xs))
    out_ref.move((out_x, 0.0))

    # --- Measurement contract: lengths.json from the Path objects (delta == delta_length). ---
    delta = bottom_len - top_len
    (Path(__file__).parent / "lengths.json").write_text(
        json.dumps(
            {"arms": {"top": top_len, "bottom": bottom_len}, "delta_length_um": delta}, indent=2
        )
    )
    return c


if __name__ == "__main__":
    comp = mzi_soi220()
    out = Path(__file__).parent / "mzi_soi220.gds"
    comp.write_gds(str(out), with_metadata=False)
    print(f"wrote {out}")
    print((Path(__file__).parent / "lengths.json").read_text())
