"""
1x4 MMI (multimode-interference) power splitter — primitives-only, parametric.

Recreated from experiments/paper_swap/final2/device_bw.png (footprint 25 x 10 um).

Topology (one input, four outputs):
    - a solid multimode SLAB (the big rectangle) where the input mode self-images,
    - ONE tapered input access waveguide entering the slab from the bottom,
    - FOUR tapered output access waveguides leaving the slab at the top,
      each sitting at a self-image position.

Calibration frame (from compare_absolute / calculate_calibration):
    footprint_um = [length=25, width=10] maps as
      X (horizontal / transverse)  <- footprint length  = 25 um   (LEFT-ALIGNED)
      Y (vertical  / propagation)  <- footprint width   = 10 um   (CENTERED)
    so the device is built with X in [0, 25] and Y in [0, 10]; the four output
    tips sit at Y=10 (image top), the input tip at Y=0 (image bottom).

Everything is composed from primitives only: rectangle, taper, gf.Path+extrude.
No gf.components device stencils, no raw polygons.
"""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

# ============================ PARAMETRIC CONTRACT ============================
# Fabrication layer for all geometry.
LAYER = (1, 0)

# ---- MMI multimode slab (the big rectangle) --------------------------------
mmi_width = 25.0          # transverse width of the slab (X)  -> fills footprint length  [FUNCTION KNOB]
mmi_length = 5.06         # propagation length of the slab (Y)  -> self-imaging length    [FUNCTION KNOB]
body_bottom_y = 1.25      # Y of the slab's input (bottom) edge in the 10um frame

# ---- single-mode access waveguide ------------------------------------------
wg_width = 1.57           # single-mode access-waveguide (guide) width                    [guide width]
taper_base_width = 3.10   # access-waveguide width where the taper meets the slab         [FUNCTION KNOB]

# ---- four OUTPUT access waveguides (top): taper + straight ------------------
output_centers_um = [3.435, 8.801, 15.771, 21.501]  # transverse self-image port positions [FUNCTION KNOB]
output_taper_length = 1.89     # output taper length (wg_width -> taper_base_width)         [FUNCTION KNOB]
output_straight_length = 1.80  # output access straight length (outputs 2..4)               [FUNCTION KNOB]
probe_length = 1.80            # output-1 access straight length -- the VERIFIED guide-width knob
#                               (equal to output_straight_length at base, so all four
#                                outputs are identical in the delivered device)

# ---- ONE INPUT access waveguide (bottom): a single truncated taper ---------
input_taper_length = 1.25      # input taper length (taper_base_width -> input_tip_width)   [FUNCTION KNOB]
input_tip_width = 1.50         # input waveguide tip width at the footprint edge

HERE = Path(__file__).resolve().parent


@gf.cell
def mmi_1x4() -> gf.Component:
    c = gf.Component()
    body_top_y = body_bottom_y + mmi_length

    # ---- multimode slab: rectangle, lower-left at (0, body_bottom_y) ----
    body = c << gf.components.rectangle(size=(mmi_width, mmi_length), layer=LAYER)
    body.dmove((0.0, body_bottom_y))

    # ---- four output access waveguides ----
    for i, cx in enumerate(output_centers_um):
        straight_len = probe_length if i == 0 else output_straight_length

        # taper: wide base (taper_base_width) at the slab top edge, narrowing UP to wg_width.
        # After drotate(90) the taper's o1 (width1) stays at the origin and the body runs +Y.
        tap = c << gf.components.taper(
            length=output_taper_length,
            width1=taper_base_width,
            width2=wg_width,
            layer=LAYER,
        )
        tap.drotate(90)
        tap.dmove((cx, body_top_y))

        # straight access section above the taper, up toward the output tip at Y=10.
        y0 = body_top_y + output_taper_length
        c << gf.path.extrude(
            gf.Path([(cx, y0), (cx, y0 + straight_len)]),
            width=wg_width,
            layer=LAYER,
        )

    # ---- input access waveguide: one truncated taper, base at the slab bottom ----
    # After drotate(-90) the taper's o1 (wide) stays at the origin and the body runs -Y.
    itap = c << gf.components.taper(
        length=input_taper_length,
        width1=taper_base_width,
        width2=input_tip_width,
        layer=LAYER,
    )
    itap.drotate(-90)
    itap.dmove((mmi_width / 2.0, body_bottom_y))

    return c


def _write_lengths(path: Path) -> None:
    """Parametric measurement contract: two OUTPUT access arms, self-measured.

    output-1 (the verified knob) and output-4 are symmetric access waveguides;
    their centerline lengths are equal at base (delta = 0). Perturbing
    ``probe_length`` lengthens ONLY output-1, so |L1 - L4| tracks it 1:1.
    """
    arm_out1 = probe_length + output_taper_length            # output-1 access centerline
    arm_out4 = output_straight_length + output_taper_length  # output-4 access centerline
    payload = {
        "arms": {"out1_access_um": arm_out1, "out4_access_um": arm_out4},
        "delta_length_um": abs(arm_out1 - arm_out4),
    }
    path.write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    comp = mmi_1x4()
    gds_path = HERE / "device.gds"
    # with_metadata=False suppresses kfactory's $$$CONTEXT_INFO$$$ cell, which
    # otherwise references the top cell and makes it non-top-level — that hides
    # the geometry from tools (e.g. spec_optimization._layer_area) that iterate
    # library.top_level() and skip $$$ cells. compare_absolute is unaffected.
    comp.write_gds(gds_path, with_metadata=False)
    _write_lengths(HERE / "lengths.json")
    try:
        bb = comp.dbbox()
        print(f"wrote {gds_path.name}  bbox_um=({bb.left:.3f},{bb.bottom:.3f})-({bb.right:.3f},{bb.top:.3f})")
    except Exception:
        print(f"wrote {gds_path.name}  bbox={comp.bbox()}")
