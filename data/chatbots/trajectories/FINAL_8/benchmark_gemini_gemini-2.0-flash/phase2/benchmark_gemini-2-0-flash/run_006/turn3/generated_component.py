import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()

    width = 120.0  # Maximum width
    height = 4.0  # Maximum height
    layer = (1, 0)

    # Explicitly set centered=False, so the rectangle starts at (0,0)
    rect = c << gf.components.rectangle(size=(width, height), layer=layer, centered=False)

    # No need to move, since centered=False starts at (0,0)

    return c

device = my_device()
device.show()
device.write_gds("my_device.gds")