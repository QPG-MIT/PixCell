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

    # Function to create positioned taper component
    def create_positioned_taper(pos, rot, length, w1, w2):
        comp = gf.Component()
        tap = comp << gf.components.taper(length=length, width1=w1, width2=w2, layer=layer)
        tap.rotate(rot)
        tap.move(pos)
        return comp

    # Base component
    base_comp = gf.Component()
    base = base_comp << gf.components.rectangle(size=(footprint_width, h_base), layer=layer, centered=True)
    base.move((0, 1 + h_base / 2))

    # Bottom taper component
    bottom_comp = create_positioned_taper((0, 1), -90, h_bottom, bottom_wide, 0)

    # Top taper components
    top_comps = []
    for cx in centers:
        top_comp = create_positioned_taper((cx, 1 + h_base), 90, h_taper, wide, 0)
        top_comps.append(top_comp)

    # Collect all parts
    all_parts = [base_comp, bottom_comp] + top_comps

    # Union all parts iteratively
    combined = all_parts[0]
    for p in all_parts[1:]:
        combined = gf.boolean(combined, p, operation="or", layer=layer)

    # Final component
    c = gf.Component()
    c << combined

    return c

# Create and save
device = my_device()
device.write_gds("my_device.gds")