"""4-port lens-taper waveguide crossing, recreated from device_bw.png (primitives only)."""
import gdsfactory as gf

# --- Tunables (top-level, JEE-substitutable). Function knobs for a crossing:
# port width, taper lengths, tip width, lens max width.
_scale = 4.7 / 4.68       # correction so the footprint lands exactly on 4.7 um
wg_width = 0.222 * _scale          # single-mode port waveguide width (um)
port_stub_length = 0.04 * _scale   # straight stub length at each footprint edge (um)
taper_up_length = 1.7855 * _scale  # port-width -> lens-max-width taper length (um)
taper_down_length = 0.5125 * _scale # lens-max-width -> tip taper length (um)
lens_max_width = 1.012 * _scale    # widest point of the multimode crossing belly (um)
lens_tip_width = 0.058 * _scale    # residual width at the center tip of each petal (um)

LAYER = (1, 0)


def _cross_section(width):
    width = round(width / 0.002) * 0.002
    return gf.cross_section.cross_section(width=width, layer=LAYER)


@gf.cell
def crossing_arm():
    """One arm, built outward from the device center (x=0): tip -> widen to
    lens_max_width -> narrow to wg_width -> straight port stub at the footprint edge."""
    c = gf.Component()

    tip = c << gf.components.straight(
        length=1e-3, cross_section=_cross_section(lens_tip_width)
    )

    down = gf.path.transition(
        cross_section1=_cross_section(lens_tip_width),
        cross_section2=_cross_section(lens_max_width),
        width_type="sine",
    )
    down_path = gf.path.straight(length=taper_down_length, npoints=200)
    down_ref = c << gf.path.extrude_transition(down_path, down)

    up = gf.path.transition(
        cross_section1=_cross_section(lens_max_width),
        cross_section2=_cross_section(wg_width),
        width_type="sine",
    )
    up_path = gf.path.straight(length=taper_up_length, npoints=200)
    up_ref = c << gf.path.extrude_transition(up_path, up)

    stub = c << gf.components.straight(
        length=port_stub_length, cross_section=_cross_section(wg_width)
    )

    # Chain: tip (at origin) -> widen -> narrow -> straight stub, outward along +x.
    down_ref.connect("o1", tip.ports["o2"])
    up_ref.connect("o1", down_ref.ports["o2"])
    stub.connect("o1", up_ref.ports["o2"])
    return c


@gf.cell
def crossing():
    """Four-fold symmetric lens-taper waveguide crossing, arms meeting at the origin."""
    c = gf.Component()
    arm = crossing_arm()

    polys = []
    for angle in (0, 90, 180, 270):
        ref = c << arm
        ref.rotate(angle)
        polys.append(ref)

    union = gf.boolean(A=polys[0], B=polys[1], operation="or", layer=LAYER)
    for p in polys[2:]:
        union = gf.boolean(A=union, B=p, operation="or", layer=LAYER)

    out = gf.Component()
    out << union
    return out


if __name__ == "__main__":
    comp = crossing()
    comp.write_gds("device.gds")
