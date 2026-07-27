"""1x4 MMI power splitter — primitives-only, parametric GDSFactory recreation.

Recreated from experiments/paper_swap/final2/device_bw.png (footprint [25,10] um).
Built with primitives only: rectangle (MMI body), taper + straight (access ports).
Geometry on layer (1,0). Coordinates fill the 25x10 (x,y) footprint box so the
anisotropic rasterizer in compare_absolute overlays the source figure.

Parametric contract:
- All tunables are top-level `name = value` assignments (JEE-substitutable).
- Function knobs (mmi_length, mmi_width, wg_width, taper widths/lengths, port
  pitch) are top-level.
- Writes lengths.json next to the GDS with delta_length_um = in_access_length
  (the verified constant-width knob).
"""

import json
from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

# ---- Top-level tunables (function knobs) ---------------------------------
# Multimode interference region (the splitter body)
mmi_width = 25.0        # transverse width of multimode region (x-extent), um
mmi_length = 5.05       # propagation length of multimode region (y-extent), um

# Single-mode access waveguides
wg_width = 1.56         # single-mode access guide width, um

# Output ports (top): taper (wide@MMI -> wg_width@tip) then straight tip
n_outputs = 4
out_taper_wide = 2.90   # output taper width at MMI interface, um
out_taper_length = 2.50 # output mode-expansion taper length, um
out_straight_length = 1.20  # output single-mode straight (tip section), um
# Lateral centers of the 4 output self-images across the MMI interface
out_pitch_outer = 9.03  # |offset| of the two outer ports from center, um
out_pitch_inner = 3.48  # |offset| of the two inner ports from center, um

# Input port (bottom): taper (wide@MMI -> wg_width@tip)
in_taper_wide = 2.90    # input taper width at MMI interface, um
in_taper_length = 1.25  # input mode-expansion taper length, um
in_access_length = 0.0  # input single-mode access straight length (verified knob), um

# Derived layout anchors
_x_center = mmi_width / 2.0
_body_bottom = in_taper_length + in_access_length
_body_top = _body_bottom + mmi_length
out_centers = [
    _x_center - out_pitch_outer,
    _x_center - out_pitch_inner,
    _x_center + out_pitch_inner,
    _x_center + out_pitch_outer,
]


def _v_taper(c, comp, x_center, y_wide, direction):
    """Place a taper vertically: wide end at (x_center, y_wide), narrow end
    `length` away along `direction` (+1 up, -1 down). Wide end = e1 (width1)."""
    ref = c.add_ref(comp)
    ref.rotate(90 * direction)
    # after rotate: e1 (wide, at local x=0) sits at origin; move to anchor
    ref.move((x_center, y_wide))
    return ref


@gf.cell
def mmi_1x4() -> gf.Component:
    c = gf.Component()

    # --- Multimode interference body (rectangle primitive) ---
    body = gf.components.rectangle(
        size=(mmi_width, mmi_length), layer=LAYER, centered=False
    )
    body_ref = c.add_ref(body)
    body_ref.move((0.0, _body_bottom))

    # --- Output ports: taper (wide@top-of-body -> wg_width) + straight tip ---
    out_taper = gf.components.taper(
        length=out_taper_length, width1=out_taper_wide, width2=wg_width, layer=LAYER
    )
    out_str = gf.components.rectangle(
        size=(wg_width, out_straight_length), layer=LAYER, centered=False
    )
    for xc in out_centers:
        _v_taper(c, out_taper, xc, _body_top, direction=+1)
        s = c.add_ref(out_str)
        s.move((xc - wg_width / 2.0, _body_top + out_taper_length))

    # --- Input port: optional access straight + taper (wide@bottom-of-body) ---
    if in_access_length > 0:
        in_str = gf.components.rectangle(
            size=(wg_width, in_access_length), layer=LAYER, centered=False
        )
        s = c.add_ref(in_str)
        s.move((_x_center - wg_width / 2.0, in_taper_length))
    in_taper = gf.components.taper(
        length=in_taper_length, width1=in_taper_wide, width2=wg_width, layer=LAYER
    )
    _v_taper(c, in_taper, _x_center, _body_bottom, direction=-1)

    return c


def _write_lengths(out_dir: Path) -> None:
    # Optical path length input-tip -> one output-tip, WITHOUT the access
    # straight (arm_core) and WITH it (arm_with_access). Both computed from the
    # geometry knobs; their difference is exactly in_access_length, so
    # delta_length_um tracks the verified knob 1:1.
    arm_core = in_taper_length + mmi_length + out_taper_length + out_straight_length
    arm_with_access = arm_core + in_access_length
    lengths = {
        "arms": {
            "path_core": arm_core,
            "path_with_access": arm_with_access,
        },
        "delta_length_um": in_access_length,
    }
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))


if __name__ == "__main__":
    comp = mmi_1x4()
    out_dir = Path(__file__).parent
    gds_path = out_dir / "device.gds"
    # with_metadata=False: skip kfactory's $$$CONTEXT_INFO$$$ wrapper so the
    # device cell stays top-level (else gdstk top_level() area probes see 0).
    comp.write_gds(str(gds_path), with_metadata=False)
    _write_lengths(out_dir)
    print(f"wrote {gds_path}")
    print(f"bbox: {comp.bbox()}")
