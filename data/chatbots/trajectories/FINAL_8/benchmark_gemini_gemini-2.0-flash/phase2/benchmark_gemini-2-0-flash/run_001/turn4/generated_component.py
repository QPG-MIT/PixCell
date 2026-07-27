import gdsfactory as gf
from gdsfactory.components import rectangle, straight
from gdsfactory.cross_section import cross_section


@gf.cell
def my_device():
    c = gf.Component()
    xs = cross_section(width=1.0, layer=(1, 0))
    gap = 1  # Gap between the middle lines.
    num_lines = 5  # Number of middle lines.
    line_length = 100
    offset_x = 20  # Offset from the origin in x
    bar_thickness = 7  # Thickness of the horizontal bars
    leg_width = 5  # Width of the "legs"
    leg_length = 20  # Length of the leg's horizontal portion
    bar_vertical_offset = 25 # Vertical offset of the bars from center

    # Top and bottom horizontal bars
    top_bar = c << rectangle(size=(line_length, bar_thickness), layer=(1, 0))
    bottom_bar = c << rectangle(size=(line_length, bar_thickness), layer=(1, 0))
    top_bar.move((offset_x, bar_vertical_offset))
    bottom_bar.move((offset_x, -bar_vertical_offset))

    # Middle lines
    middle_lines = []
    middle_y_offset = -(num_lines - 1) * gap / 2  # Calculate the offset to center the lines vertically
    for i in range(num_lines):
        line = c << straight(length=line_length, cross_section=xs)
        line.move((offset_x, middle_y_offset + i * gap))
        middle_lines.append(line)

    # Create Legs
    leg1 = c << rectangle(size=(leg_length, leg_width), layer=(1, 0))
    leg1.move((0, bar_vertical_offset))  #Position it correctly to top bar

    leg2 = c << rectangle(size=(leg_length, leg_width), layer=(1, 0))
    leg2.move((0, -bar_vertical_offset))  #Position it correctly to bottom bar

    #Vertical Line Connect top/bottom bar and Legs
    vertical_line_top = c << rectangle(size=(leg_width, bar_vertical_offset - bar_thickness/2), layer=(1, 0))
    vertical_line_top.movex(leg_length)  #Align with leg
    vertical_line_top.movey(bar_thickness/2)   #Align with the center

    vertical_line_bottom = c << rectangle(size=(leg_width, bar_vertical_offset - bar_thickness/2), layer=(1, 0))
    vertical_line_bottom.movex(leg_length)  #Align with leg
    vertical_line_bottom.movey(-bar_vertical_offset + bar_thickness/2)   #Align with the center

    return c


# Create and save
device = my_device()
device.show()
device.write_gds("my_device.gds")