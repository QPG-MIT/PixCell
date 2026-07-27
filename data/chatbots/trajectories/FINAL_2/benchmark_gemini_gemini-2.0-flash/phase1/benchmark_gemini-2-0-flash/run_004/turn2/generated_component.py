import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import straight
from gdsfactory.components import taper

@gf.cell
def my_device():
    c = gf.Component("my_device")

    # Define dimensions based on visual analysis
    rect_width = 25  # Width of the main rectangle, adjusting based on the target footprint
    rect_height = 8  # Height of the main rectangle
    taper_width = 1  # Width of the top of the tapers
    taper_length = 4  # Height of tapers
    taper_base_width = 1  # We want a straight taper, setting taper base width equals to taper width.
    taper_separation = 5.5  # Separation between tapers, adjusted based on image

    taper_total_width = 4 * taper_width + 3 * taper_separation
    horizontal_offset = (rect_width - taper_total_width) / 2  # to center

    # Create main rectangle
    rect = c << rectangle(size=(rect_width, rect_height))
    rect.move((-rect_width/2, -rect_height/2))  # center rectangle to (0,0)

    # Create tapers
    for i in range(4):
      taper_x = -rect_width/2 + horizontal_offset + i * (taper_width + taper_separation)
      taper_component = c << straight(length=taper_length, width=taper_width) # using straight instead of taper
      taper_component.move((taper_x, rect_height/2))

    # Create bottom rectangle
    bottom_rect_height = 5 # adjusting the height of the bottom rectangle
    bottom_rect_width = 3 # adjusting the width of the bottom rectangle
    bottom_rect = c << rectangle(size=(bottom_rect_width, bottom_rect_height))
    bottom_rect.move((-bottom_rect_width/2, -rect_height/2 - bottom_rect_height/2))  # center to the main rectangle bottom

    c.flatten()
    return c

device = my_device()
device.write_gds("my_device.gds")