import gdsfactory as gf
from gdsfactory.component import Component

@gf.cell
def make_the_image() -> Component:
    """Recreates the geometry from the provided image using GDSFactory."""

    c = gf.Component("the_image")

    # Parameters based on the image
    rect_width = 50  # Width of the main rectangle
    rect_height = 100  # Height of the main rectangle
    bar_width = 10  # Width of the vertical bar
    bar_height = 20  # Height of the vertical bar
    bar_offset = 5  # How far the bar is from the top of the rectangle

    # Create the main rectangle
    rect = c << gf.components.rectangle(size=(rect_width, rect_height), layer=(1, 0))
    rect.ymin = 0 # Ensure it starts at y=0

    # Create the vertical bar
    bar = c << gf.components.rectangle(size=(bar_width, bar_height), layer=(1, 0))
    bar.xmin = 0  # Align to the left edge
    bar.ymax = rect.ymax - bar_offset  # Position it near the top


    return c


if __name__ == "__main__":
    image = make_the_image()
    image.show()
    image.write_gds("the_image.gds")