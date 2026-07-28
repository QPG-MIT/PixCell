"""Four-port waveguide crossing built from four lens-shaped multimode arms.

Topology (see recreation_log.json): four identical vesica-shaped slab lenses
radiate at 0/90/180/270 deg from a common centre and overlap there; each lens
is fed at its outer end by a narrow single-mode strip that runs to the device
edge.  A port field flares into its lens, the lens self-images it onto a narrow
waist at the crossing centre (low crosstalk into the orthogonal arms), and the
opposite lens re-collimates it back into the facing single-mode port.

Primitives only: catalog ``circle`` / ``rectangle`` plus boolean AND/OR.
Every function knob is a top-level assignment (JEE-substitutable).
"""

from pathlib import Path

import gdsfactory as gf

# ----------------------------------------------------------------------------
# Tunables (top-level, JEE-substitutable).  Function knobs first.
# ----------------------------------------------------------------------------
wg_width_um = 0.2363           # single-mode port width -> input waist
lens_max_width_um = 0.9175     # multimode width of the expansion region
lens_length_um = 2.085         # self-imaging (transfer) length along the arm
lens_center_offset_um = 0.8725  # lens waist position measured from the crossing
port_length_um = 0.65          # straight single-mode feed from the device edge
half_footprint_um = 2.35       # device half-size (footprint 4.7 x 4.7 um)
n_arms = 4                     # rotational multiplicity of the crossing

arc_resolution_deg = 0.2       # circle facet size used to draw the lens arcs
layer = (1, 0)


def _lens() -> gf.Component:
    """One vesica lens on the +x arm: intersection of two equal disks.

    The two disks have radius ``R`` and centres displaced by ``+/-c`` transverse
    to the arm axis, chosen so the intersection has the requested length and
    maximum width:  R = (a^2 + b^2) / (2 b),  c = R - b, with a = L/2, b = W/2.
    """
    a = 0.5 * lens_length_um
    b = 0.5 * lens_max_width_um
    radius = (a * a + b * b) / (2.0 * b)
    offset = radius - b

    disk = gf.components.circle(
        radius=radius, angle_resolution=arc_resolution_deg, layer=layer
    )

    upper = gf.Component()
    ref_u = upper << disk
    ref_u.dmove((lens_center_offset_um, -offset))

    lower = gf.Component()
    ref_l = lower << disk
    ref_l.dmove((lens_center_offset_um, offset))

    return gf.boolean(upper, lower, operation="and", layer=layer)


def _arm() -> gf.Component:
    """Lens + straight single-mode feed for the +x arm."""
    lens = _lens()

    feed = gf.Component()
    rect = feed << gf.components.rectangle(
        size=(port_length_um, wg_width_um), layer=layer, centered=True
    )
    rect.dmove((half_footprint_um - 0.5 * port_length_um, 0.0))

    return gf.boolean(lens, feed, operation="or", layer=layer)


@gf.cell
def crossing() -> gf.Component:
    """Assemble ``n_arms`` rotated arms into a single merged polygon."""
    arm = _arm()

    merged = arm
    for i in range(1, n_arms):
        rotated = gf.Component()
        ref = rotated << arm
        ref.drotate(360.0 * i / n_arms)
        merged = gf.boolean(merged, rotated, operation="or", layer=layer)

    c = gf.Component()
    c << merged
    return c


def _through_paths() -> dict[str, gf.Path]:
    """The two optical through-paths of the crossing, as gf.Path centrelines.

    A crossing has no arm imbalance: both paths run edge-to-edge through the
    common centre, so ``delta_length_um`` is 0 by the four-fold symmetry.
    """
    east_west = gf.Path([(-half_footprint_um, 0.0), (half_footprint_um, 0.0)])
    north_south = gf.Path([(0.0, -half_footprint_um), (0.0, half_footprint_um)])
    return {"east_west": east_west, "north_south": north_south}


if __name__ == "__main__":
    import json

    component = crossing()
    here = Path(__file__).resolve().parent
    out = here / "device.gds"
    # with_metadata=False: kfactory's $$$CONTEXT_INFO$$$ cell references every
    # cell in the library, which hides the real top cell from gdstk's
    # top_level() and makes layer-area measurement read 0.
    component.write_gds(out, with_metadata=False)

    arms = {name: float(path.length()) for name, path in _through_paths().items()}
    lengths = list(arms.values())
    (here / "lengths.json").write_text(
        json.dumps(
            {
                "arms": arms,
                "delta_length_um": abs(lengths[0] - lengths[1]),
                "lens_length_um": float(lens_length_um),
                "note": (
                    "Arm centrelines are the two edge-to-edge optical through-paths "
                    "of the crossing, measured from gf.Path objects at build time. "
                    "delta_length_um is 0 by construction: a four-fold-symmetric "
                    "crossing has no arm-imbalance degree of freedom."
                ),
            },
            indent=2,
        )
    )

    print(f"wrote {out}")
    print("bbox_um:", component.dbbox())
    print("arms_um:", arms)
