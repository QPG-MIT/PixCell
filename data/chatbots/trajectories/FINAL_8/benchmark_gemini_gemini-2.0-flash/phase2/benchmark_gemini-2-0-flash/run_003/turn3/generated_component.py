import gdsfactory as gf
from gdsfactory.components import rectangle, taper


@gf.cell
def waveguide_structure():
    c = gf.Component("waveguide_structure")
    line_width = 5
    line_spacing = 5
    num_lines = 4
    length = 100
    taper_length = 20
    taper_width1 = line_width
    max_length = length + 2 * taper_length

    for i in range(num_lines):
        # Calculate line length based on index
        line_length = length - (i * 10)  # Adjust length for each line
        x_offset = (max_length - line_length) / 2  # Centering the line
        y = i * (line_width + line_spacing)

        # Taper before the line
        taper_left = c << taper(length=taper_length, width1=taper_width1, width2=1)
        taper_left.movex(0).movey(y)

        # The line
        rect = c << rectangle(size=(line_length, line_width), layer=(1, 0), centered=False)
        rect.movex(taper_length + x_offset).movey(y)  # Move the rectangle to the calculated position

        # Taper after the line
        taper_right = c << taper(length=taper_length, width1=1, width2=taper_width1)
        taper_right.movex(taper_length + line_length + x_offset).movey(y)

    return c

structure = waveguide_structure()
structure.show()
structure.write_gds("waveguide_structure.gds")