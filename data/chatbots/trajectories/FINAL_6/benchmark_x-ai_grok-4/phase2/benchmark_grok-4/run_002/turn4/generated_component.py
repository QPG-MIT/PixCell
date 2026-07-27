import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)
    a = 4.7 / 2
    points = [
        (a, 0),
        (0, a),
        (-a, 0),
        (0, -a),
    ]
    c.add_polygon(points, layer=layer)
    return c

device = my_device()
device.write_gds("my_device.gds")