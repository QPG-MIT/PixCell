"""Dual U-bend delay lines - tight bends to fit 120x4 um footprint"""
import gdsfactory as gf

# Top-level tunables
wg_width = 0.55
bend_radius = 1.0
u_depth = 1.0
straight_length = 59.0  # (120 - 2*1) / 2 = 59

layer = (1, 0)


@gf.cell
def u_bend_pair():
    """Two U-bend waveguides fitting 120x4 footprint"""
    c = gf.Component()

    # TOP PATH: straight right → U-bend upward → straight left
    top_path = gf.Path()
    top_path.append(gf.path.straight(length=straight_length))
    top_path.append(gf.path.euler(radius=bend_radius, angle=180, p=0.5))
    top_path.append(gf.path.straight(length=straight_length))

    top_wg = top_path.extrude(width=wg_width, layer=layer)
    top_ref = c << top_wg
    top_ref.move((0, u_depth))

    # BOTTOM PATH: straight right → U-bend downward → straight left
    bottom_path = gf.Path()
    bottom_path.append(gf.path.straight(length=straight_length))
    bottom_path.append(gf.path.euler(radius=bend_radius, angle=-180, p=0.5))
    bottom_path.append(gf.path.straight(length=straight_length))

    bottom_wg = bottom_path.extrude(width=wg_width, layer=layer)
    bottom_ref = c << bottom_wg
    bottom_ref.move((0, -u_depth))

    return c


if __name__ == "__main__":
    component = u_bend_pair()
    component.write_gds("device.gds")
    print(f"GDS written")
