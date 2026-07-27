import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import taper

@gf.cell
def my_device():
    c = gf.Component("my_device")

    # Define dimensions based on visual analysis, fine-tuned to the footprint constraint.
    rect_width = 24  # Adjusted main rectangle width
    rect_height = 7  # Adjusted main rectangle height
    taper_width = 1  # Width of the top of the tapers
    taper_length = 3 # Adjusted taper height
    taper_base_width = 2  # Wider base for the tapers, this is width2 now.
    taper_separation = 5.5  # Separation between tapers

    taper_total_width = 4 * taper_width + 3 * taper_separation
    horizontal_offset = (rect_width - taper_total_width) / 2  # to center

    # Create main rectangle
    rect = c << rectangle(size=(rect_width, rect_height))
    rect.move((-rect_width/2, -rect_height/2))  # center rectangle to (0,0)

    # Create tapers
    for i in range(4):
      taper_x = -rect_width/2 + horizontal_offset + i * (taper_width + taper_separation)
      taper_component = c << taper(length=taper_length, width1=taper_width, width2=taper_base_width)  # Using taper component
      taper_component.move((taper_x, rect_height/2))

    # Create bottom rectangle
    bottom_rect_height = 3  # adjusting the height of the bottom rectangle
    bottom_rect_width = 2  # adjusting the width of the bottom rectangle
    bottom_rect = c << rectangle(size=(bottom_rect_width, bottom_rect_height))
    bottom_rect.move((-bottom_rect_width/2, -rect_height/2 - bottom_rect_height/2))  # center to the main rectangle bottom

    c.flatten()
    return c

device = my_device()
device.write_gds("my_device.gds")