"""1x4 MMI power splitter — primitives-only parametric recreation (Phase A).

Center-fed multimode-interference splitter: one input access taper (bottom,
on the slab axis) feeds a wide multimode slab; four output access tapers on
the opposite face sit on the symmetric-interference image positions and
compress into single-mode wires. Geometry lives in the calibrated image
frame (see recreation_log.json); the 40 nm 'frame fiducial' pins the GDS
bbox to that frame (bbox left edge -> u=0, bbox v-center -> v=5) so the
absolute-scale renderer places the silhouette on the target ink. It is
non-functional, declared, and derived from the same tunables.
"""

from pathlib import Path
import json

import gdsfactory as gf

# ---- function-defining tunables (um) ------------------------------------
mmi_width_um = 19.462          # multimode-body width (sets L_pi ~ W^2)
mmi_length_um = 3.7533         # self-imaging length (primary function knob)
wg_width_um = 1.25             # single-mode wire width
out_center_1_um = 5.446        # output port centers (image positions)
out_center_2_um = 9.625
out_center_3_um = 15.042
out_center_4_um = 19.504
out_taper_width_1_um = 2.436   # per-port access-taper base widths (at slab)
out_taper_width_2_um = 2.464
out_taper_width_3_um = 2.450
out_taper_width_4_um = 2.506
out_taper_length_1_um = 1.295  # per-port access-taper lengths
out_taper_length_2_um = 1.343
out_taper_length_3_um = 1.331
out_taper_length_4_um = 1.422
out_straight_length_1_um = 1.425  # wire lengths to the figure edge (tips co-linear
out_straight_length_2_um = 1.390  # at v=9.143 in the base build; port 1 is drawn
out_straight_length_3_um = 1.402  # ~13 nm shorter in the figure)
out_straight_length_4_um = 1.311
in_center_um = 12.493          # center feed (symmetric interference)
in_taper_width_um = 2.466      # input access-taper base width (at slab; even-nm grid)
in_tip_width_um = 1.228        # input taper tip width (cropped at figure edge)
in_taper_length_um = 0.925     # input access-taper length

# ---- calibrated-frame constants (see recreation_log.json) ----------------
slab_left_um = 2.762           # slab left edge in the calibrated frame
slab_bottom_um = 2.6564        # slab bottom edge in the calibrated frame
frame_height_um = 10.0         # calibration footprint height
fiducial_size_um = 0.04        # frame fiducial (non-functional, declared)

LAYER = (1, 0)


@gf.cell
def mmi_1x4_splitter() -> gf.Component:
    c = gf.Component()

    # multimode body
    slab = c.add_ref(
        gf.components.rectangle(size=(mmi_width_um, mmi_length_um), layer=LAYER)
    )
    slab.move((slab_left_um, slab_bottom_um))
    slab_top = slab_bottom_um + mmi_length_um

    # four output access tapers + single-mode wires
    outputs = (
        (out_center_1_um, out_taper_width_1_um, out_taper_length_1_um, out_straight_length_1_um),
        (out_center_2_um, out_taper_width_2_um, out_taper_length_2_um, out_straight_length_2_um),
        (out_center_3_um, out_taper_width_3_um, out_taper_length_3_um, out_straight_length_3_um),
        (out_center_4_um, out_taper_width_4_um, out_taper_length_4_um, out_straight_length_4_um),
    )
    for cx, base_w, taper_len, wire_len in outputs:
        tp = c.add_ref(
            gf.components.taper(
                length=taper_len,
                width1=base_w,
                width2=wg_width_um,
                cross_section="strip",
            )
        )
        tp.rotate(90)
        tp.move((cx, slab_top))
        st = c.add_ref(
            gf.components.straight(
                length=wire_len, width=wg_width_um, cross_section="strip"
            )
        )
        st.rotate(90)
        st.move((cx, slab_top + taper_len))

    # input access taper, pointing down from the slab bottom (drawn cropped
    # at the figure edge: taper only, no straight lead)
    tin = c.add_ref(
        gf.components.taper(
            length=in_taper_length_um,
            width1=in_taper_width_um,
            width2=in_tip_width_um,
            cross_section="strip",
        )
    )
    tin.rotate(-90)
    tin.move((in_center_um, slab_bottom_um))

    # frame fiducial: pins bbox left to u=0 and bbox v-center to v=5 so the
    # absolute-scale renderer maps this frame onto the target ink.
    top_v = slab_top + max(t + s for _, _, t, s in outputs)
    fid = c.add_ref(
        gf.components.rectangle(size=(fiducial_size_um, fiducial_size_um), layer=LAYER)
    )
    fid.move((0.0, frame_height_um - top_v))

    return c


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    component = mmi_1x4_splitter()
    # with_metadata=False: skip kfactory's $$$CONTEXT_INFO$$$ cell so the real
    # top cell is the GDS top-level (what the measurement tooling reads).
    component.write_gds(out_dir / "device.gds", with_metadata=False)

    # measurement contract: lengths from the script's OWN path objects.
    # The two 'arms' are the propagation distances from the input facet to
    # the two planes bounding the multimode body; their difference IS the
    # self-imaging length mmi_length_um (the primary function knob).
    p_in = gf.path.straight(length=in_taper_length_um)
    p_mmi = gf.path.straight(length=mmi_length_um)
    lengths = {
        "arms": {
            "input_facet_to_mmi_entry": p_in.length(),
            "input_facet_to_mmi_exit": p_in.length() + p_mmi.length(),
        },
        "delta_length_um": p_mmi.length(),
        "note": (
            "1x4 MMI splitter: delta between the propagation planes bounding "
            "the multimode body = self-imaging length (knob mmi_length_um), "
            "computed from gf.Path objects at build time."
        ),
    }
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    print(f"wrote {out_dir / 'device.gds'} and lengths.json")
