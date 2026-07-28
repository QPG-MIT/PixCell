"""Four-port waveguide crossing with elliptical lens tapers — primitives only.

Each arm: straight stub -> elliptical width expansion -> flat top at max width
-> elliptical contraction to the crossing center. Four rotated copies unioned.
"""

import numpy as np
import gdsfactory as gf

# ---- function-defining tunables (um) ----
stub_width_um = 0.236        # access waveguide width (guided mode)
stub_length_um = 0.55        # port lead length
taper_up_length_um = 0.89    # lens expansion length (adiabaticity / focus)
lens_max_width_um = 0.910    # expanded beam width at lens waist
flat_length_um = 0.16        # flat top at max width
taper_down_length_um = 0.75  # contraction toward the crossing center
center_tip_width_um = 0.30   # arm width where it reaches the center
taper_shape_exp = 0.86       # fullness exponent of the sine lens profile

LAYER = (1, 0)
_NPTS = 201  # dense path sampling so transitions follow the profile


def _lens_up(t, w0, w1):
    """Lens widening: w0 -> w1 with a sine^exp profile (full flanks)."""
    return w0 + (w1 - w0) * np.sin(np.pi * np.asarray(t) / 2) ** taper_shape_exp


def _lens_down(t, w0, w1):
    """Mirror image: flat near the wide end, fast near the center tip."""
    return w1 + (w0 - w1) * np.sin(np.pi * (1 - np.asarray(t)) / 2) ** taper_shape_exp


def _snap(width):
    """Port widths must be multiples of 2 dbu (0.002 um)."""
    return round(width / 0.002) * 0.002


def _xs(width):
    return gf.cross_section.cross_section(width=_snap(width), layer=LAYER)


@gf.cell
def crossing_arm() -> gf.Component:
    """One arm, from outer port tip (x=0) to the crossing center."""
    c = gf.Component()
    x = 0.0

    stub = c << gf.path.extrude(gf.path.straight(length=stub_length_um), _xs(stub_width_um))
    stub.dmovex(x)
    x += stub_length_um

    t_up = gf.path.transition(_xs(stub_width_um), _xs(lens_max_width_um), width_type=_lens_up)
    up = c << gf.path.extrude_transition(
        gf.path.straight(length=taper_up_length_um, npoints=_NPTS), t_up
    )
    up.dmovex(x)
    x += taper_up_length_um

    flat = c << gf.path.extrude(gf.path.straight(length=flat_length_um), _xs(lens_max_width_um))
    flat.dmovex(x)
    x += flat_length_um

    t_dn = gf.path.transition(_xs(lens_max_width_um), _xs(center_tip_width_um), width_type=_lens_down)
    dn = c << gf.path.extrude_transition(
        gf.path.straight(length=taper_down_length_um, npoints=_NPTS), t_dn
    )
    dn.dmovex(x)
    return c


@gf.cell
def crossing() -> gf.Component:
    c = gf.Component()
    half = stub_length_um + taper_up_length_um + flat_length_um + taper_down_length_um
    for angle in (0, 90, 180, 270):
        ref = c << crossing_arm()
        ref.dmovex(-half)  # outer tip at -half, inner end at center (0,0)
        ref.drotate(angle)
    return c


if __name__ == "__main__":
    import json
    from pathlib import Path

    here = Path(__file__).parent
    comp = crossing()
    comp.write_gds(here / "crossing.gds", with_metadata=False)

    # Measurement contract: lengths computed from the path objects, not typed in.
    half = sum(
        gf.path.straight(length=seg).length()
        for seg in (stub_length_um, taper_up_length_um, flat_length_um, taper_down_length_um)
    )
    arms = {"through_horizontal_um": 2 * half, "through_vertical_um": 2 * half}
    lengths = {
        "arms": arms,
        "delta_length_um": abs(arms["through_horizontal_um"] - arms["through_vertical_um"]),
    }
    (here / "lengths.json").write_text(json.dumps(lengths, indent=2))
