import gdsfactory as gf

@gf.cell
def my_device():
    layer = (1, 0)

    # Dimensions
    footprint_width = 25
    footprint_height = 10
    wide = footprint_width / 4  # 6.25
    bottom_wide = wide
    pitch = wide
    h_base = 2
    h_taper = 7
    h_bottom = 1

    centers = [-1.5 * pitch, -0.5 * pitch, 0.5 * pitch, 1.5 * pitch]

    # Positioned base
    positioned_base = gf.Component()
    base = gf.components.rectangle(size=(footprint_width, h_base), layer=layer, centered=True)
    base_ref = positioned_base << base
    base_ref.move((0, 1 + h_base / 2))
    unioned = positioned_base

    # Positioned bottom taper
    positioned_bottom = gf.Component()
    bottom_tap = gf.components.taper(length=h_bottom, width1=bottom_wide, width2=0, layer=layer)
    bottom_ref = positioned_bottom << bottom_tap
    bottom_ref.rotate(-90)
    bottom_ref.move((0, 1 + 0.01))
    unioned = gf.boolean(unioned, positioned_bottom, operation="or", layer=layer)

    # Positioned top tapers
    for cx in centers:
        positioned_top = gf.Component()
        top_tap = gf.components.taper(length=h_taper, width1=wide, width2=0, layer=layer)
        top_ref = positioned_top << top_tap
        top_ref.rotate(90)
        top_ref.move((cx, 1 + h_base - 0.01))
        unioned = gf.boolean(unioned, positioned_top, operation="or", layer=layer)

    return unioned

# Create and save
device = my_device()
device.write_gds("my_device.gds")