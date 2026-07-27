import gdsfactory as gf
from gdsfactory.components import rectangle


@gf.cell
def waveguide_structure():
    c = gf.Component("waveguide_structure")
    line_width = 5
    line_spacing = 5
    num_lines = 4
    total_height = (num_lines * line_width) + ((num_lines - 1) * line_spacing)
    length = 100

    for i in range(num_lines):
        y = i * (line_width + line_spacing)
        rect = c << rectangle(size=(length, line_width), layer=(1, 0), centered=False)
        rect.movey(y)

    return c

structure = waveguide_structure()
structure.show()
structure.write_gds("waveguide_structure.gds")