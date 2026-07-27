import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import straight
from gdsfactory.components import bend_euler
from gdsfactory.cross_section import cross_section


@gf.cell
def my_device():
    c = gf.Component()
    xs = cross_section(width=1.0, layer=(1, 0), radius=5)  # Setting radius_min=5
    gap = 1.0
    num_lines = 3
    line_length = 20
    bend_radius = 5
    offset_x = 20  # Offset from the origin in x

    # Rectangles on the left
    rect1 = c << rectangle(size=(10, 15), layer=(1, 0))
    rect2 = c << rectangle(size=(10, 15), layer=(1, 0))
    rect1.movex(offset_x)
    rect1.movey(15)
    rect2.movex(offset_x)
    rect2.movey(-15)

    # Vertical lines on the right
    lines = []
    for i in range(num_lines):
        line = c << straight(length=30, cross_section=xs)
        line.movex(offset_x + 10 + i * (xs.width + gap))
        lines.append(line)

    # Bends on the rectangles
    bend1 = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend1.rotate(180)  # Rotate bend 180 degrees to connect properly
    # The ports on rectangle will not connect automatically.  Will need to adjust or add custom ports
    bend1.movex(offset_x + 10)
    bend1.movey(22.5)


    bend2 = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend2.rotate(90)
    # The ports on rectangle will not connect automatically.  Will need to adjust or add custom ports
    bend2.movex(offset_x + 10)
    bend2.movey(-22.5)


    return c


# Create and save
device = my_device()
device.show()
device.write_gds("my_device.gds")