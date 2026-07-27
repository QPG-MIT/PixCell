import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import straight
from gdsfactory.cross_section import cross_section
import numpy as np


@gf.cell
def my_device():
    c = gf.Component()
    xs = cross_section(width=1.0, layer=(1, 0))
    gap = 0.2  # Gap between the middle lines.
    num_lines = 5  # Number of middle lines.
    line_length = 50
    offset_x = 20  # Offset from the origin in x
    bar_thickness = 7  # Thickness of the horizontal bars
    leg_width = 5  # Width of the "legs"
    leg_length = 10  # Length of the leg's horizontal portion

    # Top and bottom horizontal bars
    top_bar = c << rectangle(size=(line_length + offset_x, bar_thickness), layer=(1, 0))
    bottom_bar = c << rectangle(size=(line_length + offset_x, bar_thickness), layer=(1, 0))
    top_bar.movey(25)
    bottom_bar.movey(-25)

    # Middle lines
    middle_lines = []
    for i in range(num_lines):
        line = c << straight(length=line_length, cross_section=xs)
        line.movex(offset_x)
        line.movey(-gap * (num_lines // 2 - i))  # Centering the lines
        middle_lines.append(line)

    # Create Legs
    leg1 = c << rectangle(size=(leg_length, bar_thickness), layer=(1, 0))
    leg1.movex(offset_x)
    leg1.movey(0)

    leg2 = c << rectangle(size=(leg_length, bar_thickness), layer=(1, 0))
    leg2.movex(offset_x)
    leg2.movey(-0)

    # Connect Top bars with legs
    v_line_top = c << straight(length=25-bar_thickness/2, cross_section=xs)
    v_line_top.movex(offset_x+leg_length-1)
    v_line_top.movey(bar_thickness/2)

    v_line_bottom = c << straight(length=25-bar_thickness/2, cross_section=xs)
    v_line_bottom.movex(offset_x+leg_length-1)
    v_line_bottom.movey(-25+bar_thickness/2)

    return c


# Create and save
device = my_device()
device.show()
device.write_gds("my_device.gds")