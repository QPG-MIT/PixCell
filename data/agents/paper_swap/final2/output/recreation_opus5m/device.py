"""1x4 MMI power splitter — primitives-only parametric recreation.

Topology: one tapered input access waveguide -> rectangular multimode slab ->
four tapered output access waveguides. Propagation is along +y (input at the
bottom edge, outputs at the top edge), matching the target drawing.

Built only from gf.Path + extrude (straights, linear-width tapers) and a
rectangle. No gf.components device stencils, no raw polygons.
"""

import gdsfactory as gf

# ---------------------------------------------------------------------------
# Tunables (top-level, JEE-substitutable). Function knobs of a 1xN MMI.
# ---------------------------------------------------------------------------
layer = (1, 0)

# multimode slab — sets the self-imaging condition
mmi_width_um = 25.0
mmi_length_um = 5.053

# input access waveguide
in_taper_length_um = 1.256
in_taper_tip_width_um = 1.528
in_taper_wide_width_um = 3.176
in_port_offset_um = 0.0  # lateral launch offset from slab center

# output access waveguides
out_taper_length_um = 1.826
out_taper_wide_width_um = 3.182
out_straight_length_um = 1.865
wg_width_um = 1.584

# lateral positions of the four self-images, relative to the slab center
out_port_offsets_um = [-9.052, -3.693, 3.266, 8.989]

# fabrication / meshing
taper_overlap_um = 0.05  # access tapers stub into the slab so the union is clean


def _cs(width: float) -> gf.CrossSection:
    return gf.cross_section.cross_section(width=width, layer=layer)


def _linear_taper(length: float, width1: float, width2: float) -> gf.Component:
    """A straight linear-width transition built from a Path + extrude."""
    p = gf.Path()
    p.append(gf.path.straight(length=length))
    trans = gf.path.transition(_cs(width1), _cs(width2), width_type="linear")
    return gf.path.extrude_transition(p, trans)


def _straight(length: float, width: float) -> gf.Component:
    p = gf.Path()
    p.append(gf.path.straight(length=length))
    return gf.path.extrude(p, cross_section=_cs(width))


@gf.cell
def mmi_1x4() -> gf.Component:
    c = gf.Component()

    x_center = mmi_width_um / 2.0
    y_slab_0 = in_taper_length_um
    y_slab_1 = y_slab_0 + mmi_length_um

    # --- multimode slab -----------------------------------------------------
    slab = c << gf.components.rectangle(
        size=(mmi_width_um, mmi_length_um), layer=layer, centered=False
    )
    slab.dmovey(y_slab_0)

    # --- input access waveguide (taper, tip truncated at the footprint edge)
    in_taper = c << _linear_taper(
        in_taper_length_um + taper_overlap_um,
        in_taper_tip_width_um,
        in_taper_wide_width_um,
    )
    in_taper.drotate(90)
    in_taper.dmove((x_center + in_port_offset_um, 0.0))

    # --- four output access waveguides --------------------------------------
    for offset in out_port_offsets_um:
        x = x_center + offset

        out_taper = c << _linear_taper(
            out_taper_length_um + taper_overlap_um,
            out_taper_wide_width_um,
            wg_width_um,
        )
        out_taper.drotate(90)
        out_taper.dmove((x, y_slab_1 - taper_overlap_um))

        out_wg = c << _straight(out_straight_length_um, wg_width_um)
        out_wg.drotate(90)
        out_wg.dmove((x, y_slab_1 + out_taper_length_um))

    return c


def arm_paths() -> dict[str, gf.Path]:
    """Input-tip -> output-port centerline of each branch, as gf.Path objects.

    The lateral fan-out happens inside the multimode slab (self-imaging), not
    through bends, so every branch centerline is the same straight sequence:
    input taper -> slab -> output taper -> output straight.
    """
    paths: dict[str, gf.Path] = {}
    for i, _offset in enumerate(out_port_offsets_um, start=1):
        p = gf.Path()
        for seg in (
            in_taper_length_um,
            mmi_length_um,
            out_taper_length_um,
            out_straight_length_um,
        ):
            p.append(gf.path.straight(length=seg))
        paths[f"o{i}"] = p
    return paths


def write_lengths(path: str = "lengths.json") -> dict:
    """Optical path lengths measured from the centerline Paths (never hand-entered)."""
    import json

    arms = {name: float(p.length()) for name, p in arm_paths().items()}
    data = {
        "arms": arms,
        # A 1xN MMI splitter is path-length balanced by construction: every
        # branch shares the same longitudinal sequence, so the arm imbalance is
        # identically zero. There is no arm-imbalance knob in this topology.
        "delta_length_um": float(max(arms.values()) - min(arms.values())),
        "propagation_length_um": float(next(iter(arms.values()))),
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return data


if __name__ == "__main__":
    comp = mmi_1x4()
    comp.write_gds("device.gds")
    print("bbox:", comp.dbbox())
    print("lengths:", write_lengths())
