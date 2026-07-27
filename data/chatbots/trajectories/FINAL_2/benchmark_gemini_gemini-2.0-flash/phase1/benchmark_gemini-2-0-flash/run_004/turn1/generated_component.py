import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import straight
from gdsfactory.components import taper

@gf.cell
def my_device():
    c = gf.Component("my_device")

    # Define dimensions based on visual analysis
    rect_width = 20  # Width of the main rectangle
    rect_height = 8  # Height of the main rectangle
    taper_width = 1 # Width of the top of the tapers
    taper_length = 4
    taper_base_width = 1.5 # Estimating base width
    taper_separation = 3.5  # Separation between tapers

    taper_total_width = 4 * taper_width + 3 * taper_separation
    horizontal_offset = (rect_width - taper_total_width) / 2 # to center
    # Create main rectangle
    rect = c << rectangle(size=(rect_width, rect_height))
    rect.move((-rect_width/2, -rect_height/2)) # center rectangle to (0,0)

    # Create tapers
    for i in range(4):
      taper_x = -rect_width/2 + horizontal_offset + i * (taper_width + taper_separation)
      # print(taper_x)
      taper_component = c << taper(length=taper_length, width1=taper_base_width, width2=taper_width)
      taper_component.move((taper_x + taper_width / 2 - taper_component.x,rect_height/2 ))


    # Create bottom rectangle
    bottom_rect_height = 2
    bottom_rect_width = 1.5
    bottom_rect = c << rectangle(size=(bottom_rect_width, bottom_rect_height))
    bottom_rect.move((-bottom_rect_width/2, -rect_height/2 - bottom_rect_height)) # center

    c.flatten()
    return c

device = my_device()
# device.show() # Remove this line
device.write_gds("my_device.gds") # Save the component to a GDS file