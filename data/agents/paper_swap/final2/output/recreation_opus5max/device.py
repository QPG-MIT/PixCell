"""1x4 multimode-interference (MMI) power splitter -- parametric recreation.

Recreated from data/agents/paper_swap/final2/device_bw.png (footprint 25 x 10 um).

TOPOLOGY
--------
One uniform rectangular multimode slab (mmi_width x mmi_length) with a single
centred, tapered access port on its input edge and four tapered access ports on
its output edge. Light launched through the input taper excites a superposition
of the slab's lateral modes; those modes beat with a common beat length
L_pi = 4 n_g W_e^2 / (3 lambda) and reconstruct the input field as N self-images
at 3 L_pi / (4 N). The four output ports sit on the N = 4 image plane, so the
device splits one input into four nominally equal outputs. The linear tapers at
both ends widen the single-mode field before it enters (and after it leaves) the
slab, which is what keeps the imaging loss low.

The function-defining knobs are therefore mmi_length (which image plane the
output edge lands on), mmi_width (which sets L_pi and the lateral image
spacing), the four out_offset_* (the ports must sit on the image spots),
taper_width and the taper lengths (excitation and collection efficiency).

Every segment is built by extruding a gf.Path, so the centreline lengths written
to lengths.json are measured from the objects that made the geometry.

CONTRACT
--------
Primitives only: gf.Path + gf.path.extrude / gf.path.extrude_transition, layer
(1, 0), tunables as top-level assignments, ends with write_gds. No device
stencils from gf.components, no raw polygons, no image reads.
"""

from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf

# --------------------------------------------------------------------------
# Tunables (um).  Every one is a top-level `name = value` assignment.
# --------------------------------------------------------------------------

layer_num = 1
layer_dtype = 0

# Every value is a 50%-luminance (true edge) measurement of the figure, scaled
# by the footprint annotation: the slab spans the full 25 um width (1371.24 px
# -> 54.849 px/um) and the stub-top-to-input-tip span is the full 10 um height
# (1682.12 px -> 168.212 px/um).  The four lengths below therefore close to
# exactly 10.0000 um and the slab to exactly 25.0000 um, which is the
# self-consistency check that this frame, not the halo-inflated one, is right.

# --- multimode interference region: the splitter core -------------------
mmi_width = 25.0            # slab width W_mmi; sets L_pi ~ W_e^2 and image pitch
mmi_length = 5.0639         # slab length: THE self-imaging knob (picks the N=4 plane)

# --- output access waveguides (4x, on the far edge of the slab) ---------
wg_width = 1.5716           # single-mode access width
taper_width = 3.1604        # taper wide end, where it meets the slab
out_taper_length = 1.8810   # adiabatic length of the output tapers
out_straight_length = 1.8100  # single-mode output bus drawn inside the footprint

# --- output port positions, measured from the slab centre ---------------
# These must coincide with the four self-image spots.  Kept as four
# independent knobs because the figure's pitch is not uniform.
out_offset_1 = -9.0626
out_offset_2 = -3.6973
out_offset_3 = 3.2763
out_offset_4 = 9.0166

# --- input access waveguide (1x, centred on the slab) -------------------
in_taper_length = 1.2451    # adiabatic length of the input taper
in_tip_width = 1.5510       # input bus width where the footprint crops it
in_offset = 0.0             # input port offset from the slab centre (measured -0.0018)

GRID_UM = 0.002             # kfactory requires port widths on a 2 nm grid


def _snap(width: float) -> float:
    """Snap a width to the 2 nm grid kfactory requires for cross sections."""
    return round(round(width / GRID_UM) * GRID_UM, 6)


def _xs(width: float) -> gf.CrossSection:
    return gf.cross_section.cross_section(width=_snap(width), layer=(layer_num, layer_dtype))


def _vpath(x: float, y0: float, y1: float) -> gf.Path:
    """A straight centreline at x, running from y0 to y1."""
    return gf.Path([(x, y0), (x, y1)])


@gf.cell
def mmi_1x4() -> gf.Component:
    """Assemble the 1x4 MMI splitter and stash its measured centrelines."""
    c = gf.Component()

    # --- multimode slab: a path of length mmi_length, mmi_width wide ----
    slab_path = _vpath(0.0, 0.0, mmi_length)
    c.add_ref(gf.path.extrude(slab_path, cross_section=_xs(mmi_width)))

    # --- four tapered output access waveguides --------------------------
    out_to_narrow = gf.path.transition(_xs(taper_width), _xs(wg_width), width_type="linear")
    taper_top = mmi_length + out_taper_length
    out_top = taper_top + out_straight_length

    out_taper_path = None
    out_straight_path = None
    for offset in (out_offset_1, out_offset_2, out_offset_3, out_offset_4):
        out_taper_path = _vpath(offset, mmi_length, taper_top)
        out_straight_path = _vpath(offset, taper_top, out_top)
        c.add_ref(gf.path.extrude_transition(out_taper_path, out_to_narrow))
        c.add_ref(gf.path.extrude(out_straight_path, cross_section=_xs(wg_width)))

    # --- input taper: same wide end, cropped at the footprint edge ------
    in_to_narrow = gf.path.transition(_xs(taper_width), _xs(in_tip_width), width_type="linear")
    in_taper_path = _vpath(in_offset, 0.0, -in_taper_length)
    c.add_ref(gf.path.extrude_transition(in_taper_path, in_to_narrow))

    # Centreline lengths, measured from the gf.Path objects above.
    c.info["len_slab"] = slab_path.length()
    c.info["len_in_taper"] = in_taper_path.length()
    c.info["len_out_taper"] = out_taper_path.length()
    c.info["len_out_straight"] = out_straight_path.length()
    return c


def write_lengths(component: gf.Component, path: Path) -> dict:
    """Write the measured centreline lengths next to the GDS.

    This device is a 1x4 splitter, not an MZI, so it has no two interfering
    arms.  homi.spec_optimization._validate_arms nevertheless requires exactly
    two entries whose difference is delta_length_um, so the two entries are the
    on-axis optical path measured WITH and WITHOUT the multimode section:
    their difference is the multimode section length itself, which is this
    device's primary function knob (mmi_length).  Both numbers come from the
    gf.Path objects that built the geometry, never hand-entered.
    """
    access = (
        component.info["len_in_taper"]
        + component.info["len_out_taper"]
        + component.info["len_out_straight"]
    )
    through = access + component.info["len_slab"]
    payload = {
        "arms": {
            "axis_through_mmi": through,
            "axis_single_mode_access_only": access,
        },
        "delta_length_um": through - access,
        "note": (
            "1x4 MMI splitter, not an MZI: the two entries are the on-axis "
            "optical path with and without the multimode slab, so their "
            "difference is the self-imaging length mmi_length."
        ),
    }
    path.write_text(json.dumps(payload, indent=2))
    return payload


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    component = mmi_1x4()
    write_lengths(component, here / "lengths.json")
    # with_metadata=False drops kfactory's $$$CONTEXT_INFO$$$ cell.  That cell
    # references the device, which would leave the device cell non-top-level and
    # make homi's _layer_area (top-cells only) measure 0 um^2.
    component.write_gds(here / "device.gds", with_metadata=False)
    bbox = component.dbbox()
    print(f"bbox um: {bbox.width():.4f} x {bbox.height():.4f}")
