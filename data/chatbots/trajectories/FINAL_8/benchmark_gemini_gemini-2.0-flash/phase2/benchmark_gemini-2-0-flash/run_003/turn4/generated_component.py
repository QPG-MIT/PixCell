import gdsfactory as gf
from gdsfactory.components import rectangle, taper


@gf.cell
def waveguide_structure():
    c = gf.Component("waveguide_structure")
    line_width = 3  # Reduced line width
    line_spacing = 3
    num_lines = 7  # Increased number of lines
    length = 90
    taper_length = 10  # Reduced taper length
    taper_width1 = 3  # Starting taper width (same as line_width)
    taper_width2 = 0.4   # Final taper width

    total_structure_height = (num_lines - 1) * (line_width + line_spacing)

    for i in range(num_lines):
        # Calculate the Y position for each line, centering the structure
        y = i * (line_width + line_spacing) - total_structure_height / 2

        # Taper before the line
        taper_left = c << taper(length=taper_length, width1=taper_width1, width2=taper_width2)
        taper_left.movex(0).movey(y)

        # The line
        rect = c << rectangle(size=(length, line_width), layer=(1, 0), centered=False)
        rect.movex(taper_length).movey(y)

        # Taper after the line
        taper_right = c << taper(length=taper_length, width1=taper_width2, width2=taper_width1)
        taper_right.movex(taper_length + length).movey(y)

    return c


structure = waveguide_structure()
structure.show()
structure.write_gds("waveguide_structure.gds")