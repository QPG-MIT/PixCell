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
    bend_radius: float = 1.0, # Adjust this for the curve radius
    layer=(1, 0)
) -> Component:
    """Recreates the geometry with multiple horizontal lines and curves."""

    c = gf.Component("the_image")

    num_lines_top = 5 # Specific count from the target image
    num_lines_mid = 5 # Specific count from the target image
    num_lines_bot = 5 # Specific count from the target image


    def create_curved_line_path(length, bend_radius):
        """Creates a path with curved ends."""
        straight_length = length - 2 * bend_radius  #Adjust the length of the straight section according to the bend.
        if straight_length < 0:  # handle the short width scenario
            bend_radius = length / 2
            straight_length = 0
        p = gf.Path()
        p.append(gf.path.arc(radius=bend_radius, angle=90))
        p.append(gf.path.straight(length=straight_length))
        p.append(gf.path.arc(radius=bend_radius, angle=90))
        return p


    # Create top section
    top_section = gf.Component("top_section")
    for i in range(num_lines_top):
        y = i * (line_width + line_spacing)
        path = create_curved_line_path(width - 0.1, bend_radius)
        line = top_section << gf.path.extrude(path, width=line_width, layer=layer)
        line.move((0, y))

    top_section.flatten()
    top = c << top_section
    top.ymax = height

    # Create middle section
    mid_section = gf.Component("mid_section")
    for i in range(num_lines_mid):
        y = i * (line_width + line_spacing)
        path = gf.path.straight(width)  # create_curved_line_path(width, bend_radius)
        line = mid_section << gf.path.extrude(path, width=line_width, layer=layer) #gf.components.rectangle(size=(width, line_width), layer=layer)
        line.move((0, y))

    mid_section.flatten()
    mid = c << mid_section
    mid.ymax = height / 2


    # Create bottom section
    bot_section = gf.Component("bot_section")
    for i in range(num_lines_bot):
        y = i * (line_width + line_spacing)
        path = create_curved_line_path(width - 0.1, bend_radius)
        line = bot_section << gf.path.extrude(path, width=line_width, layer=layer)
        line.move((0, y))

    bot_section.flatten()
    bot = c << bot_section
    bot.ymin = 0 # Ensure starts at y=0


    return c


if __name__ == "__main__":
    image = make_the_image()
    image.show()
    image.write_gds("the_image.gds")