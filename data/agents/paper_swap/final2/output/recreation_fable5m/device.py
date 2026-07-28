"""1x4 MMI power splitter — primitives-only parametric recreation.

Topology: single tapered input port (bottom, centered) -> rectangular
multimode slab -> four tapered output ports (top). Self-imaging in the slab
produces the 4-fold image plane at y = mmi_length_um.

Coordinates are microns in the calibrated 25x10 frame (y up). The renderer
anchors this script's bbox left edge to the calibration bbox left edge and
centers it vertically on the footprint; frame_left_margin_um /
frame_bottom_margin_um plus two tiny frame-anchor slivers reproduce the
device's position inside that frame (declared in recreation_log.json).
"""

import json
from pathlib import Path

import gdsfactory as gf

LAYER = (1, 0)

# --- function-defining tunables (um) ---
mmi_width_um = 19.43          # multimode slab width (transverse)
mmi_length_um = 3.75          # multimode slab length (propagation) — primary knob
taper_tip_width_um = 1.22     # single-mode guide width at every port tip
taper_end_width_um = 2.47     # access taper width at the slab interface
out_taper_length_um = 1.31    # output access taper length
out_stub_length_um = 1.42     # straight single-mode stub above each output taper
in_taper_length_um = 0.93     # input access taper length
in_taper_end_width_um = 2.42  # input taper width at the slab interface

# output port centers, offsets from slab center (um) — as drawn (not symmetric)
port1_offset_um = -7.05
port2_offset_um = -2.88
port3_offset_um = 2.54
port4_offset_um = 7.00
in_offset_um = -0.01          # input port center offset from slab center

# --- frame placement tunables (um) ---
frame_left_margin_um = 2.78    # slab left edge relative to the scoring-frame left
frame_bottom_margin_um = 0.87  # input taper tip height above the scoring bbox bottom
anchor_size_um = 0.04          # frame-anchor slivers (set bbox left/bottom edges)


@gf.cell
def mmi_1x4() -> gf.Component:
    c = gf.Component()

    slab_x0 = frame_left_margin_um
    slab_y0 = frame_bottom_margin_um + in_taper_length_um
    slab_cx = slab_x0 + mmi_width_um / 2
    slab_y1 = slab_y0 + mmi_length_um

    slab = c.add_ref(gf.components.rectangle(size=(mmi_width_um, mmi_length_um), layer=LAYER))
    slab.dmove((slab_x0, slab_y0))

    # output ports: taper (wide at slab, narrow up) + straight stub
    for offset in (port1_offset_um, port2_offset_um, port3_offset_um, port4_offset_um):
        cx = slab_cx + offset
        tap = c.add_ref(
            gf.components.taper(
                length=out_taper_length_um,
                width1=taper_end_width_um,
                width2=taper_tip_width_um,
                layer=LAYER,
            )
        )
        tap.drotate(90)  # +x -> +y: wide end down
        tap.dmove((cx - tap.dcenter[0], slab_y1 - tap.dymin))
        stub = c.add_ref(
            gf.components.rectangle(size=(taper_tip_width_um, out_stub_length_um), layer=LAYER)
        )
        stub.dmove((cx - taper_tip_width_um / 2, slab_y1 + out_taper_length_um))

    # input port: taper (wide at slab, narrow down), truncated tip as drawn
    in_cx = slab_cx + in_offset_um
    itap = c.add_ref(
        gf.components.taper(
            length=in_taper_length_um,
            width1=in_taper_end_width_um,
            width2=taper_tip_width_um,
            layer=LAYER,
        )
    )
    itap.drotate(-90)  # +x -> -y: wide end up
    itap.dmove((in_cx - itap.dcenter[0], slab_y0 - itap.dymax))

    # frame-anchor slivers: pin the bbox left and bottom edges to the scoring frame
    anchor_l = c.add_ref(
        gf.components.rectangle(size=(anchor_size_um, anchor_size_um), layer=LAYER)
    )
    anchor_l.dmove((0.0, slab_y0 + mmi_length_um / 2))
    anchor_b = c.add_ref(
        gf.components.rectangle(size=(anchor_size_um, anchor_size_um), layer=LAYER)
    )
    anchor_b.dmove((in_cx - anchor_size_um / 2, 0.0))

    return c


if __name__ == "__main__":
    component = mmi_1x4()
    out = Path(__file__).parent
    # with_metadata=False drops kfactory's $$$CONTEXT_INFO$$$ cell, which
    # references every cell and defeats gdstk top_level()-based area measurement
    component.write_gds(out / "mmi_1x4.gds", with_metadata=False)

    # measured from the built geometry (contract: never hand-entered; the
    # lengths.json schema is MZI-shaped — exactly 2 arms — so for this MMI the
    # two "arms" are the port-to-port propagation path through the slab and the
    # same path excluding the slab: their difference IS the slab length knob).
    bbox = component.dbbox()
    path_total = bbox.top - bbox.bottom - frame_bottom_margin_um  # tip-to-tip path
    path_access = path_total - mmi_length_um  # tapers + output stub only
    lengths = {
        "arms": {"port_to_port": path_total, "access_only": path_access},
        "delta_length_um": path_total - path_access,
    }
    (out / "lengths.json").write_text(json.dumps(lengths, indent=2))
    print(f"wrote mmi_1x4.gds; bbox={component.dbbox()}")
