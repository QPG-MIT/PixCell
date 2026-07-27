import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.component import Component

@gf.cell
def device():
    c = Component("device")

    # Base rectangle dimensions
    rect_width = 20
    rect_height = 10

    # Top Pin dimensions at the top and bottom, respectively
    pin_top_width = 3
    pin_bottom_width = 6
    pin_height = 7

    # Bottom pin dimensions
    bottom_pin_top_width = 3
    bottom_pin_bottom_width = 6
    bottom_pin_height = 3

    # Spacing between pins
    pin_spacing = (rect_width - 4 * pin_top_width) / 3  # Calculate even spacing

    # Create the base rectangle
    rect = c << rectangle(size=(rect_width, rect_height), layer=(1, 0))
    rect.movex(-rect_width / 2)
    rect.movey(-rect_height / 2)

    # Create the top pins
    for i in range(4):
        # Points for the tapered pin (trapezoid)
        points = [
            (-pin_bottom_width / 2, 0),
            (pin_bottom_width / 2, 0),
            (pin_top_width / 2, pin_height),
            (-pin_top_width / 2, pin_height),
        ]
        pin = c << gf.components.polygon(points=points, layer=(1, 0))

        # Position pins
        pin.movex(-rect_width / 2 + i * (pin_top_width + pin_spacing) - (pin_top_width - pin_bottom_width) / 2)
        pin.movey(rect_height / 2)

    # Create the bottom pin
    bottom_pin_points = [
        (-bottom_pin_bottom_width / 2, 0),
        (bottom_pin_bottom_width / 2, 0),
        (bottom_pin_top_width / 2, -bottom_pin_height),
        (-bottom_pin_top_width / 2, -bottom_pin_height),
    ]

    bottom_pin = c << gf.components.polygon(points=bottom_pin_points, layer=(1, 0))
    bottom_pin.movex(-bottom_pin_top_width / 2)  # Center pin horizontally
    bottom_pin.movey(-rect_height / 2 - bottom_pin_height)  # Place pin closer to rectangle

    return c

# Create and save
device = device()
device.show()
device.write_gds("device.gds")