"""Dual waveguide crossing - two independent optical paths crossing via S-bends"""
import gdsfactory as gf

# Top-level tunables
wg_width = 0.55
vertical_offset = 1.5
sbend_length = 30.0
crossing_length = 20.0
straight_section = 15.0

layer = (1, 0)


@gf.cell
def waveguide_crossing():
    c = gf.Component()

    # TOP PATH
    top_path = gf.Path()
    top_path.append(gf.path.straight(length=straight_section))
    top_path.append(gf.path.euler(radius=10.0, angle=90, p=0.5))
    top_path.append(gf.path.straight(length=sbend_length - 20.0))
    top_path.append(gf.path.euler(radius=10.0, angle=-90, p=0.5))
    top_path.append(gf.path.straight(length=crossing_length))
    top_path.append(gf.path.euler(radius=10.0, angle=-90, p=0.5))
    top_path.append(gf.path.straight(length=sbend_length - 20.0))
    top_path.append(gf.path.euler(radius=10.0, angle=90, p=0.5))
    top_path.append(gf.path.straight(length=straight_section))

    top_waveguide = top_path.extrude(width=wg_width, layer=layer)
    top_ref = c << top_waveguide
    top_ref.move((0, vertical_offset))

    # BOTTOM PATH
    bottom_path = gf.Path()
    bottom_path.append(gf.path.straight(length=straight_section))
    bottom_path.append(gf.path.euler(radius=10.0, angle=-90, p=0.5))
    bottom_path.append(gf.path.straight(length=sbend_length - 20.0))
    bottom_path.append(gf.path.euler(radius=10.0, angle=90, p=0.5))
    bottom_path.append(gf.path.straight(length=crossing_length))
    bottom_path.append(gf.path.euler(radius=10.0, angle=90, p=0.5))
    bottom_path.append(gf.path.straight(length=sbend_length - 20.0))
    bottom_path.append(gf.path.euler(radius=10.0, angle=-90, p=0.5))
    bottom_path.append(gf.path.straight(length=straight_section))

    bottom_waveguide = bottom_path.extrude(width=wg_width, layer=layer)
    bottom_ref = c << bottom_waveguide
    bottom_ref.move((0, -vertical_offset))

    return c


if __name__ == "__main__":
    component = waveguide_crossing()
    component.write_gds("device.gds")
    print(f"GDS written")
