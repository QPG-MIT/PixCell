"""Unbalanced Mach-Zehnder interferometer, recreated from mzi_input.png.

Primitives-only, parametric GDSFactory (9.20.7). Topology extracted from the
image (see reasoning.md):

    input -> coupler1 (splitter bar) -> {top arm, bottom arm racetrack detours}
          -> coupler2 (combiner bar) -> output

Each arm is a gf.Path built from straight + euler(90) primitives. The bottom
arm is taller than the top by `delta_length` total (each of its two walls is
delta_length/2 longer), so the two arms' path lengths differ by exactly
`delta_length` (the FSR knob). Couplers are `gf.components.rectangle` (a basic
shape). No device stencils, no raw polygons.
"""

import json
from pathlib import Path

import gdsfactory as gf

# ---------------------------------------------------------------------------
# Tunables (top-level `name = value`, JEE-substitutable). MUST include delta_length.
# ---------------------------------------------------------------------------
wg_width = 1.0  # waveguide width (um), layer (1,0)
coupler_length = 5.4  # length of each solid coupler bar (um)
coupler_width = 2.5  # height/thickness of each coupler bar (um)
bend_radius_in = 7.5  # euler radius for the fan-out / return bends near center (um)
bend_radius_cap = 7.3  # euler radius for the top/bottom cap corners (um)
arm_lead = 9.078  # horizontal lead from coupler edge to the fan-out bend (um)
arm_vertical_top = 1.54  # TOP racetrack straight-wall height (um) -> sets top reach ~22.5 um
arm_cap = 0.223  # horizontal cap length of both racetracks (um)
delta_length = 10.6  # arm path-length imbalance (um): the FSR knob. Realized as the
# BOTTOM arm being taller than the top (each of its two vertical
# walls is delta_length/2 longer), so bottom_len - top_len ==
# delta_length exactly and the bottom racetrack reaches deeper,
# matching the drawing. Perturbing it moves real geometry.
arm_gap = 0.7  # center-to-center separation of the two arms near the couplers (um)
coupler1_cx = 12.7  # x-center of the left coupler bar (um)
device_length = 91.1  # total footprint length (um); output straight fills to here

# The bottom racetrack is taller than the top (by delta_length total): this matches
# the drawing (bottom reaches ~28 um below the centerline, top ~22.5 um above) AND
# places the device bbox center below the waveguide centerline, so the compare tool's
# vertical centering lands the centerline at ~22.7 um from the top, where the target's is.

LAYER = (1, 0)
_xs = gf.cross_section.cross_section(width=wg_width, layer=LAYER)


def _arm_path(sign: int, vertical: float) -> gf.Path:
    """Racetrack-detour arm centerline. sign=+1 up, -1 down.

    Tight `bend_radius_in` fan-out/return bends keep the arms near the centerline
    until they turn steeply up/down into near-vertical walls (as in the image);
    rounder `bend_radius_cap` corners form the top/bottom caps. Both arms share the
    same cap and radii; only the wall `vertical` differs (bottom is taller).
    """
    p = gf.Path()
    p += gf.path.straight(length=arm_lead)
    p += gf.path.euler(radius=bend_radius_in, angle=sign * 90)  # steep turn up/down
    p += gf.path.straight(length=vertical)
    p += gf.path.euler(radius=bend_radius_cap, angle=-sign * 90)  # rounded cap corner to +x
    p += gf.path.straight(length=arm_cap)
    p += gf.path.euler(radius=bend_radius_cap, angle=-sign * 90)  # rounded cap corner to -y/+y
    p += gf.path.straight(length=vertical)
    p += gf.path.euler(radius=bend_radius_in, angle=sign * 90)  # steep return bend to +x
    p += gf.path.straight(length=arm_lead)
    return p


@gf.cell
def mzi_recreated() -> gf.Component:
    c = gf.Component()

    # Arm centerlines (Path objects -> lengths measured from these, never hand-entered).
    # The bottom arm's two walls are each delta_length/2 taller than the top arm's,
    # so bottom_len - top_len == delta_length by construction.
    arm_vertical_bot = arm_vertical_top + delta_length / 2.0
    top_path = _arm_path(+1, arm_vertical_top)
    bottom_path = _arm_path(-1, arm_vertical_bot)
    top_len = float(top_path.length())
    bottom_len = float(bottom_path.length())

    # Couplers (solid bars) as basic-shape rectangles.
    coupler1_right = coupler1_cx + coupler_length / 2.0
    c.add_ref(
        gf.components.rectangle(size=(coupler_length, coupler_width), layer=LAYER, centered=True)
    ).move((coupler1_cx, 0.0))

    # Place both arms at the right edge of coupler1, offset by +-arm_gap/2 so they run
    # as two parallel guides near the couplers (as in the image) before fanning out.
    top_ref = c.add_ref(gf.path.extrude(top_path, cross_section=_xs))
    top_ref.move((coupler1_right, +arm_gap / 2.0))
    bot_ref = c.add_ref(gf.path.extrude(bottom_path, cross_section=_xs))
    bot_ref.move((coupler1_right, -arm_gap / 2.0))

    # Arm ends (they return to the centerline); combiner sits at their right edge.
    arm_end_x = float(top_ref.ports["o2"].center[0])
    coupler2_cx = arm_end_x + coupler_length / 2.0
    c.add_ref(
        gf.components.rectangle(size=(coupler_length, coupler_width), layer=LAYER, centered=True)
    ).move((coupler2_cx, 0.0))

    # Input straight: left image edge (x=0) into coupler1.
    coupler1_left = coupler1_cx - coupler_length / 2.0
    in_ref = c.add_ref(gf.path.extrude(gf.path.straight(length=coupler1_left), cross_section=_xs))
    in_ref.move((0.0, 0.0))

    # Output straight: coupler2 right edge to the far image edge (x=device_length).
    coupler2_right = coupler2_cx + coupler_length / 2.0
    out_len = max(device_length - coupler2_right, 0.5)
    out_ref = c.add_ref(gf.path.extrude(gf.path.straight(length=out_len), cross_section=_xs))
    out_ref.move((coupler2_right, 0.0))

    # --- Measurement contract: write lengths.json from the Path objects. ---
    # Reported imbalance is the TRUE arm-length difference measured from the paths;
    # by construction it equals `delta_length` (the bottom arm is that much taller),
    # so perturbing `delta_length` moves the reported imbalance 1:1 and grows real
    # layer-(1,0) area -- the JEE / spec_optimization knob-response contract.
    delta = bottom_len - top_len
    lengths = {
        "arms": {"top": top_len, "bottom": bottom_len},
        "delta_length_um": delta,
    }
    (Path(__file__).parent / "lengths.json").write_text(json.dumps(lengths, indent=2))
    return c


if __name__ == "__main__":
    comp = mzi_recreated()
    out = Path(__file__).parent / "mzi_recreated.gds"
    # with_metadata=False keeps the device as the top-level cell (no $$$CONTEXT_INFO$$$
    # wrapper), so gdstk-based measurement reads the real layer-(1,0) geometry.
    comp.write_gds(str(out), with_metadata=False)
    print(f"wrote {out}")
    print((Path(__file__).parent / "lengths.json").read_text())
