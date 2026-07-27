import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import triangle

@gf.cell
def my_device():
    c = gf.Component("my_device")

    # Main rectangle body
    body_width = 20
    body_height = 8
    body = c << rectangle(size=(body_width, body_height), layer=(1, 0), centered=True)

    # Bottom triangle
    bottom_triangle_width = 2
    bottom_triangle_height = 2
    bottom_triangle = c << triangle(x=bottom_triangle_width, y=bottom_triangle_height, layer=(1, 0))
    bottom_triangle.rotate(180)  # Rotate triangle to point downwards
    bottom_triangle.move((0, -body_height/2))  # position at the center bottom of the main body


    # Top "fingers"
    finger_width = 2
    finger_height = 5
    finger_spacing = 3  # Gap between fingers
    num_fingers = 4

    start_x = -((num_fingers - 1) * (finger_width + finger_spacing) / 2)

    for i in range(num_fingers):
        x_pos = start_x + i * (finger_width + finger_spacing)
        finger = c << rectangle(size=(finger_width, finger_height), layer=(1, 0), centered=True)
        finger.move((x_pos, body_height/2 + finger_height/2))


    return c

# Create and save
device = my_device()
device.show()  # display in klayout
# device.write_gds("my_device.gds")