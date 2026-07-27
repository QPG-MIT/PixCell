import gdsfactory as gf
from gdsfactory.components import rectangle

@gf.cell
def device():
    c = gf.Component("device")

    # Base rectangle dimensions
    rect_width = 20
    rect_height = 10

    # Pin dimensions
    pin_width = 3
    pin_height = 7

    # Spacing between pins
    pin_spacing = (rect_width - 4 * pin_width) / 3  # Calculate even spacing

    # Bottom pin dimension
    bottom_pin_width = 3
    bottom_pin_height = 3

    # Create the base rectangle
    rect = c << rectangle(size=(rect_width, rect_height), layer=(1, 0))
    rect.movex(-rect_width / 2)
    rect.movey(-rect_height / 2)

    # Create the top pins
    for i in range(4):
        pin = c << rectangle(size=(pin_width, pin_height), layer=(1, 0))
        pin.movex(-rect_width / 2 + i * (pin_width + pin_spacing))  # Position pins evenly
        pin.movey(rect_height / 2)  # Place pins on top of the rectangle

    # Create the bottom pin
    bottom_pin = c << rectangle(size=(bottom_pin_width, bottom_pin_height), layer=(1, 0))
    bottom_pin.movex(-bottom_pin_width / 2)  # Center pin horizontally
    bottom_pin.movey(-rect_height / 2 - bottom_pin_height)  # Place pin at the bottom

    return c

# Create and save
device = device()
device.show()
device.write_gds("device.gds")