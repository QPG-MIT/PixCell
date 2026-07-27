import gdsfactory as gf
from gdsfactory.component import Component
import numpy as np

@gf.cell
def make_the_image(
    width: float = 120.0,
    height: float = 4.0,
    line_width: float = 0.2,
    line_spacing: float = 0.1,
    section_height: float = 1.0,
    bend_amount: float = 0.5,
    layer=(1, 0)
) -> Component:
    """Recreates the geometry with multiple horizontal lines and curves."""

    c = gf.Component("the_image")

    num_lines_top = int(section_height / (line_width + line_spacing))
    num_lines_mid = num_lines_top #for now
    num_lines_bot = num_lines_top #for now

    # Function to create a line
    def create_line(x, y, length, width):
        line = c << gf.components.rectangle(size=(length, width), layer=layer)
        line.xmin = x
        line.ymin = y
        return line

    # Create top section
    top_section = gf.Component("top_section")
    for i in range(num_lines_top):
        y = i * (line_width + line_spacing)
        line = top_section << gf.components.rectangle(size=(width - bend_amount, line_width), layer=layer)
        line.xmin = bend_amount / 2
        line.ymin = y
    top_section.flatten()
    top = c << top_section
    top.ymax = height


    # Create middle section
    mid_section = gf.Component("mid_section")
    for i in range(num_lines_mid):
        y = i * (line_width + line_spacing)
        line = mid_section << gf.components.rectangle(size=(width, line_width), layer=layer)
        line.xmin = 0
        line.ymin = y
    mid_section.flatten()
    mid = c << mid_section
    mid.ymax = height / 2


    # Create bottom section
    bot_section = gf.Component("bot_section")
    for i in range(num_lines_bot):
        y = i * (line_width + line_spacing)
        line = bot_section << gf.components.rectangle(size=(width - bend_amount, line_width), layer=layer)
        line.xmin = bend_amount / 2
        line.ymin = y
    bot_section.flatten()
    bot = c << bot_section
    bot.ymin = 0 # Ensure starts at y=0

    return c

if __name__ == "__main__":
    image = make_the_image()
    image.show()
    image.write_gds("the_image.gds")