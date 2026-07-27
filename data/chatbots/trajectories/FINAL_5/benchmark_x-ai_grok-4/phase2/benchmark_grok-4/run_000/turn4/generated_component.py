import gdsfactory as gf

# Parameters
layer = (1, 0)
tooth_width = 0.1
pitch = 0.36
N_teeth = 25
L_middle = (N_teeth - 1) * pitch + tooth_width  # 8.74
total_length = 18.24
L_side = (total_length - L_middle) / 2  # 4.75
y_span = 0.7
y_max = y_span / 2
y_min = -y_max

@gf.cell
def my_device():
    c = gf.Component()

    # Middle grated region: full rectangle minus thin slots
    middle_rect_c = gf.components.rectangle(size=(L_middle, y_span), layer=layer, centered=False)

    slots = gf.Component()
    for i in range(N_teeth):
        slot = gf.components.rectangle(size=(tooth_width, y_span), layer=layer, centered=False)
        slots.add_ref(slot).move((i * pitch, 0))

    grated_middle = gf.boolean(middle_rect_c, slots, operation="not", layer=layer)
    gm = c << grated_middle
    gm.move((0, y_min))

    # Left taper (solid triangle)
    left_taper = gf.Component()
    left_taper.add_polygon([(-L_side, 0), (0, y_max), (0, y_min), (-L_side, 0)], layer=layer)
    c << left_taper

    # Right taper (solid triangle)
    right_taper = gf.Component()
    right_taper.add_polygon([(L_middle, y_max), (L_middle + L_side, 0), (L_middle, y_min), (L_middle, y_max)], layer=layer)
    c << right_taper

    return c

# Create and save
device = my_device()
device.write_gds("my_device.gds")