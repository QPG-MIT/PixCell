"""Spec-driven PDK-swap retune of the recreated MZI -- 400 nm TFLN strip (isotropic approx).

Derived from experiments/pdk_swap/output/recreation/mzi_recreated_refined.py
(the JEE-polished recreation). The TOPOLOGY is preserved -- an unbalanced
Mach-Zehnder: coupler1 (splitter bar) -> {reference arm, delay arm} -> coupler2
(combiner bar). Only the GEOMETRY morphs to meet the spec.

Physics: FSR = lambda^2 / (n_g * delta_length). Hitting FSR = 8 nm on a stack
with group index n_g needs delta_length = lambda^2 / (n_g * FSR). On TFLN
(n_g ~ 2.23) that is ~135 um -- far more path imbalance than a single vertical
excursion can hold in a compact device. So the long (bottom) arm is a boustrophedon
MEANDER built from primitives (straight + euler U-turns); the top arm is the straight
reference. The meander folds the whole delta_length into a ~57 x 45 um box.

delta_length stays the single FSR knob: finger height is solved from it so that
bottom_len - top_len == delta_length exactly (measured from the gf.Path objects).
Primitives only (straight, euler, extrude, rectangle); no device stencils, no raw polygons.
"""

import json
from pathlib import Path

import gdsfactory as gf

# ---------------------------------------------------------------------------
# Tunables (top-level `name = value`, JEE-substitutable). delta_length is the FSR knob.
# ---------------------------------------------------------------------------
wg_width = 1.2  # waveguide width (um) = stack single_mode_width_um (rule-based, TFLN)
min_feature_um = 0.5  # stack min feature (um); all widths/gaps respect it
delta_length = 134.81  # arm path-length imbalance (um): the FSR knob (== bottom_len - top_len)
meander_fingers = 4  # number of vertical fingers in the delay arm (structural, fixed)
meander_radius = 6.0  # euler radius of the meander U-turns (um); low-loss, >> min_feature
coupler_length = 5.574  # length of each solid coupler bar (um)
coupler_width = 2.568  # height/thickness of each coupler bar (um)
arm_gap = 0.9  # center-to-center separation of the two arms at the couplers (um)
coupler1_cx = 8.0  # x-center of the left (splitter) coupler bar (um)
io_lead = 8.0  # input/output straight length outside the couplers (um)

LAYER = (1, 0)
_xs = gf.cross_section.cross_section(width=wg_width, layer=LAYER)


def _meander_path(fingers: int, radius: float, finger_height: float) -> gf.Path:
    """Boustrophedon meander: `fingers` vertical straights joined by 180-deg euler
    U-turns. Starts on-axis heading +x and returns to the axis heading +x, so it
    connects two couplers like a straight would -- but longer by the folded detour."""
    p = gf.Path()
    p += gf.path.euler(radius=radius, angle=-90)  # +x -> -y (dip below axis)
    for i in range(fingers):
        p += gf.path.straight(length=finger_height)
        if i < fingers - 1:
            p += gf.path.euler(radius=radius, angle=(180 if i % 2 == 0 else -180))
    p += gf.path.euler(radius=radius, angle=(90 if (fingers - 1) % 2 == 0 else -90))
    return p


# Meander length is exactly affine in finger height: L(Fh) = _span + _g + fingers*Fh,
# where _span is the (Fh-independent) horizontal advance and _g the length at Fh=0.
# Recover _span/_g from two probe builds, then solve finger height so that
# (bottom_len - top_len) == delta_length exactly. (top arm is a straight of _span.)
_p1 = _meander_path(meander_fingers, meander_radius, 1.0)
_p2 = _meander_path(meander_fingers, meander_radius, 2.0)
_span = float(_p1.points[-1][0])
_slope = float(_p2.length() - _p1.length())  # == meander_fingers
_len_at_0 = float(_p1.length()) - _slope * 1.0
_g = _len_at_0 - _span
finger_height = (delta_length - _g) / meander_fingers
assert finger_height >= min_feature_um, (
    f"delta_length={delta_length} too small for {meander_fingers} fingers "
    f"(finger_height={finger_height:.3f} < min_feature {min_feature_um}); "
    f"reduce fingers or raise delta_length above {_g:.2f} um"
)


@gf.cell
def mzi_tfln400() -> gf.Component:
    c = gf.Component()

    # Reference (short) arm = straight of the meander's horizontal span; delay arm = meander.
    top_path = gf.path.straight(length=_span)
    bottom_path = _meander_path(meander_fingers, meander_radius, finger_height)
    top_len = float(top_path.length())
    bottom_len = float(bottom_path.length())

    coupler1_right = coupler1_cx + coupler_length / 2.0
    c.add_ref(
        gf.components.rectangle(size=(coupler_length, coupler_width), layer=LAYER, centered=True)
    ).move((coupler1_cx, 0.0))

    # Arms exit coupler1 offset by +-arm_gap/2 and both return to that y at coupler2.
    top_ref = c.add_ref(gf.path.extrude(top_path, cross_section=_xs))
    top_ref.move((coupler1_right, +arm_gap / 2.0))
    bot_ref = c.add_ref(gf.path.extrude(bottom_path, cross_section=_xs))
    bot_ref.move((coupler1_right, -arm_gap / 2.0))

    coupler2_cx = coupler1_right + _span + coupler_length / 2.0
    c.add_ref(
        gf.components.rectangle(size=(coupler_length, coupler_width), layer=LAYER, centered=True)
    ).move((coupler2_cx, 0.0))

    # Input / output straights.
    coupler1_left = coupler1_cx - coupler_length / 2.0
    in_ref = c.add_ref(gf.path.extrude(gf.path.straight(length=coupler1_left), cross_section=_xs))
    in_ref.move((0.0, 0.0))
    coupler2_right = coupler2_cx + coupler_length / 2.0
    out_ref = c.add_ref(gf.path.extrude(gf.path.straight(length=io_lead), cross_section=_xs))
    out_ref.move((coupler2_right, 0.0))

    # --- Measurement contract: lengths.json from the Path objects (delta == delta_length). ---
    delta = bottom_len - top_len
    (Path(__file__).parent / "lengths.json").write_text(
        json.dumps(
            {"arms": {"top": top_len, "bottom": bottom_len}, "delta_length_um": delta}, indent=2
        )
    )
    return c


if __name__ == "__main__":
    comp = mzi_tfln400()
    out = Path(__file__).parent / "mzi_tfln400.gds"
    comp.write_gds(str(out), with_metadata=False)
    print(f"wrote {out}")
    print((Path(__file__).parent / "lengths.json").read_text())
