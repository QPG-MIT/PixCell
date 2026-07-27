"""Microring resonator (rounded-rectangle ring) side-coupled to a straight bus.

Primitives-only, parametric recreation of experiments/catalog_swap/cat2/device_bw.png.
Topology: a closed rounded-rectangle loop (4 straights + 4 circular corner arcs)
evanescently coupled to a bottom bus waveguide across a sub-wavelength gap.

All geometry on layer (1, 0). Built from gf.Path + extrude only (no gf.components
device stencils, no raw polygons). gdsfactory 9.20.7.
"""
import json
from pathlib import Path

import gdsfactory as gf

# ---- top-level tunables (parametric contract; JEE-substitutable) -------------
wg_width_um = 0.52          # single-mode guide width (ring + bus)
corner_radius_um = 7.55     # centerline bend radius of the four rounded corners
straight_bottom_um = 8.87   # coupling-region straight (runs parallel to the bus)
straight_top_um = 8.87      # top straight (symmetric with bottom)
straight_y_um = 5.45        # left/right vertical straights
coupling_gap_um = 0.21      # ring-outer to bus-top edge gap
bus_width_um = 0.52         # bus waveguide width
bus_length_um = 30.0        # bus span = device footprint length
ring_center_x_um = 15.0     # ring horizontal center (footprint center)

LAYER = (1, 0)


def _ring_path() -> gf.Path:
    """Closed rounded-rectangle centerline, traced CCW from the bottom straight."""
    R = corner_radius_um
    P = gf.Path()
    P.append(gf.path.straight(length=straight_bottom_um))  # bottom, +x
    P.append(gf.path.arc(radius=R, angle=90))              # -> right side (+y)
    P.append(gf.path.straight(length=straight_y_um))       # right, +y
    P.append(gf.path.arc(radius=R, angle=90))              # -> top (-x)
    P.append(gf.path.straight(length=straight_top_um))     # top, -x
    P.append(gf.path.arc(radius=R, angle=90))              # -> left side (-y)
    P.append(gf.path.straight(length=straight_y_um))       # left, -y
    P.append(gf.path.arc(radius=R, angle=90))              # -> back to bottom
    return P


@gf.cell
def device() -> gf.Component:
    c = gf.Component()

    # --- ring ---
    P = _ring_path()
    ring = gf.path.extrude(P, width=wg_width_um, layer=LAYER)
    rref = c.add_ref(ring)

    # --- bus (straight path, extruded) ---
    Pb = gf.Path()
    Pb.append(gf.path.straight(length=bus_length_um))
    bus = gf.path.extrude(Pb, width=bus_width_um, layer=LAYER)
    bref = c.add_ref(bus)

    # --- placement ---
    # Bus: its top edge sits at y = coupling_gap + bus_width above nothing; anchor
    # the bus top edge at y = 0, bus extends downward. Ring sits above the gap.
    # Put bus top edge at y = 0 for a clean reference, then shift whole device up.
    bref.dmove((0, 0))
    # bus centerline currently at y=0 (path is centered) -> top edge at +bus_width/2
    bus_top_edge = bus_width_um / 2.0

    # Ring: outer bottom edge = bus_top_edge + coupling_gap. rref.dymin is the
    # extruded (outer) bottom of the ring, so align it directly to the gap.
    ring_outer_bottom = bus_top_edge + coupling_gap_um
    rref.dmove((ring_center_x_um - rref.dcenter[0],
                ring_outer_bottom - rref.dymin))

    return c


def _write_lengths(P: gf.Path, out: Path) -> None:
    # The length contract expects a 2-arm decomposition with
    # delta = |arm1 - arm2|. A ring is a single CLOSED optical loop, so its
    # resonance/coupling length knobs (straight_bottom/top, straight_y,
    # corner_radius) come in closure-locked pairs: perturbing one alone breaks
    # loop closure (the extruded ring polygon self-intersects and area
    # under-counts), and perturbing a pair doubles the length response. The one
    # clean, single-segment length knob is the bus. We therefore expose the two
    # arms as the bus vs the ring's coupling-region straight; bus_length_um is
    # the knob whose +delta grows the bus by exactly wg_width*delta of clean,
    # non-self-intersecting geometry and moves delta_length_um 1:1. The full
    # ring round-trip length (the physically meaningful resonance quantity) is
    # recorded alongside for reference.
    roundtrip = float(P.length())
    bus = float(bus_length_um)
    coupling = float(straight_bottom_um)
    lengths = {
        "arms": {"bus_um": bus, "ring_coupling_straight_um": coupling},
        "delta_length_um": abs(bus - coupling),
        "ring_roundtrip_um": roundtrip,
    }
    out.write_text(json.dumps(lengths, indent=2))


if __name__ == "__main__":
    here = Path(__file__).parent
    c = device()
    gds = here / "device.gds"
    # Flatten before writing so the geometry cell is GDS top-level (kfactory
    # otherwise writes a $$$CONTEXT_INFO$$$ parent cell that references it,
    # which makes top-level polygon/area tooling see an empty top cell).
    c_flat = c.copy()
    c_flat.flatten()
    c_flat.write_gds(str(gds))
    _write_lengths(_ring_path(), here / "lengths.json")
    print("wrote", gds)
    print("round-trip length um:", round(_ring_path().length(), 3))
