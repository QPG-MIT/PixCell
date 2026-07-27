import gdsfactory as gf
from gdsfactory.components import rectangle

@gf.cell
def my_device():
    c = gf.Component("my_device")

    # Define dimensions based on visual analysis, fine-tuned to the footprint constraint.
    rect_width = 24  # Main rectangle width (adjust if needed)
    rect_height = 6  # Main rectangle height (adjust if needed)
    taper_width = 1  # Width of the rectangular part of the taper
    taper_height = 3  # Height of the triangular part of the taper
    taper_separation = 5.5  # Separation between tapers
    bottom_rect_height = 4  # Height of bottom rectangle (increased)
    bottom_rect_width = 2   # Width of bottom rectangle

    taper_base_width = 2  # Width of base of taper triangles

    taper_total_width = 4 * taper_width + 3 * taper_separation
    horizontal_offset = (rect_width - taper_total_width) / 2

    # Create main rectangle
    rect = c << rectangle(size=(rect_width, rect_height))
    rect.move((-rect_width/2, -rect_height/2))  # center rectangle to (0,0)

    # Create tapers
    for i in range(4):
        taper_x = -rect_width/2 + horizontal_offset + i * (taper_width + taper_separation)

        # Create rectangular top
        rect_top = c << rectangle(size=(taper_width, taper_height))
        rect_top.move((taper_x, rect_height/2))

        #Create triangular bottom
        triangle = c << gf.components.triangle(x=taper_base_width, y=taper_height)
        triangle.move((taper_x - (taper_base_width - taper_width) / 2, rect_height / 2 - taper_height))

    # Create bottom rectangle
    bottom_rect = c << rectangle(size=(bottom_rect_width, bottom_rect_height))
    bottom_rect.move((-bottom_rect_width/2, -rect_height/2 - bottom_rect_height))  # Relative to main rectangle bottom

    c.flatten()
    return c

device = my_device()
device.write_gds("my_device.gds")