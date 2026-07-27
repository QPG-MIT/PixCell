import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()

    width = 60  # Adjust width as needed. Based on footprint, aim for max 120.0
    height = 4  # Adjust height as needed, aim for max 4.0. Keep very small
    layer = (1, 0)

    rect = c << gf.components.rectangle(size=(width, height), layer=layer, centered=False)  # Explicitly set centered=False

    # Move to the left edge to make it fit within the component
    rect.movex(-width / 2)
    rect.movey(-height/2)

    return c

device = my_device()
device.show()
device.write_gds("my_device.gds")