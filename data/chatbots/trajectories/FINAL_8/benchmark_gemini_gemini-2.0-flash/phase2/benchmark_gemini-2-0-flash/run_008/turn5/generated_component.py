import gdsfactory as gf

@gf.cell
def interlaced_lines(width=1, line_spacing=0.2, num_lines=5, line_length=20, vertical_gap=4):
    """
    Creates an interlaced pattern of horizontal lines with vertical connectors on each end.

    Args:
        width (float): Width of the lines.
        line_spacing (float): Spacing between the lines.
        num_lines (int): Number of lines in each interlaced section.
        line_length (float): Length of individual lines.
        vertical_gap (float): Gap between the interlaced sections.
    """
    c = gf.Component("interlaced_lines")

    section_width = (num_lines - 1) * line_spacing + width

    # Create a function for a single line
    def create_line(length, y_offset):
        line = gf.components.rectangle(size=(length, width), layer=(1, 0), centered=False)
        line_ref = c << line
        line_ref.movey(y_offset)
        return line_ref

    # Helper function to correctly calculate y position of the line.
    def calculate_line_y(i, section_width, section_y_start):
        return section_y_start + i * (width + line_spacing)

    # Create top section
    top_y_start = vertical_gap / 2
    for i in range(num_lines):
        y = calculate_line_y(i, section_width, top_y_start)
        create_line(line_length, y)

    # Create bottom section
    bottom_y_start = -vertical_gap / 2 - section_width + width
    for i in range(num_lines):
        y = calculate_line_y(i, section_width, bottom_y_start)
        create_line(line_length, y)

    # Vertical Connecting Bars
    vertical_bar_width = width
    vertical_bar_length = vertical_gap + section_width
    vertical_bar_x_left = -line_length/2 - vertical_bar_width/2
    vertical_bar_x_right = line_length/2 + vertical_bar_width/2

    # Top Left Bar
    top_vertical_bar_left = c << gf.components.rectangle(size=(vertical_bar_width, vertical_bar_length), layer=(1, 0), centered=True)
    top_vertical_bar_left.movey(vertical_gap/2 + section_width/2)
    top_vertical_bar_left.movex(vertical_bar_x_left)

    #Bottom Left Bar
    bottom_vertical_bar_left = c << gf.components.rectangle(size=(vertical_bar_width, vertical_bar_length), layer=(1, 0), centered=True)
    bottom_vertical_bar_left.movey(-vertical_gap/2 - section_width/2)
    bottom_vertical_bar_left.movex(vertical_bar_x_left)

    # Top Right Bar
    top_vertical_bar_right = c << gf.components.rectangle(size=(vertical_bar_width, vertical_bar_length), layer=(1, 0), centered=True)
    top_vertical_bar_right.movey(vertical_gap/2 + section_width/2)
    top_vertical_bar_right.movex(vertical_bar_x_right)

    #Bottom Right Bar
    bottom_vertical_bar_right = c << gf.components.rectangle(size=(vertical_bar_width, vertical_bar_length), layer=(1, 0), centered=True)
    bottom_vertical_bar_right.movey(-vertical_gap/2 - section_width/2)
    bottom_vertical_bar_right.movex(vertical_bar_x_right)

    #Middle Line, using Top Parameters
    middle_y_start = 0
    for i in range(num_lines):
        y = calculate_line_y(i, section_width, middle_y_start)
        create_line(line_length, y)

    return c

if __name__ == "__main__":
    c = interlaced_lines(num_lines=5, line_length=50, width=2, line_spacing = 0.5, vertical_gap = 10)
    c.show()
    c.write_gds("interlaced_lines.gds")