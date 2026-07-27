import gdsfactory as gf
from gdsfactory.components import rectangle, taper


@gf.cell
def waveguide_structure():
    c = gf.Component("waveguide_structure")
    line_width = 0.4  # Narrower line width
    line_spacing = 2
    num_lines = 11  # Increased number of lines
    length = 90
    taper_length = 10
    taper_width1 = 3  # Starting taper width
    taper_width2 = line_width  # Final taper width matches line width

    total_structure_height = (num_lines - 1) * (line_spacing + line_width)

    for i in range(num_lines):
        # Calculate the Y position for each line, centering the structure
        y = i * (line_width + line_spacing) - total_structure_height / 2

        # Taper before the line
        taper_left = c << taper(length=taper_length, width1=taper_width1, width2=taper_width2)
        taper_left.movex(0).movey(y - line_width / 2) # Subtract half of line_width for centering

        # The line
        rect = c << rectangle(size=(length, line_width), layer=(1, 0), centered=False)
        rect.movex(taper_length).movey(y - line_width / 2) # Subtract half of line_width for centering

        # Taper after the line
        taper_right = c << taper(length=taper_length, width1=taper_width1, width2=taper_width2)
        taper_right.rotate(180)  # Taper needs to be flipped, remove keyword degrees
        taper_right.movex(taper_length + length).movey(y - line_width/2) # Shift to make it fit

    return c


structure = waveguide_structure()
structure.show()
structure.write_gds("waveguide_structure.gds")