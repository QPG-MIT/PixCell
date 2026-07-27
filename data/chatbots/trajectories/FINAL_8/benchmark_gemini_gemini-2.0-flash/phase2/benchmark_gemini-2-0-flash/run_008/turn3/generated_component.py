import gdsfactory as gf

@gf.cell
def interlaced_lines(width=1, line_spacing=0.2, num_lines=5, line_length=20, vertical_gap=4):
    """
    Creates an interlaced pattern of horizontal lines with vertical connectors.

    Args:
        width (float): Width of the lines.
        line_spacing (float): Spacing between the lines.
        num_lines (int): Number of lines in each interlaced section.
        line_length (float): Length of individual lines.
        vertical_gap (float): Gap between the interlaced sections.
    """
    c = gf.Component("interlaced_lines")

    section_width = line_spacing * (num_lines - 1) + width * num_lines

    # Create a function for a single line
    def create_line(length, y_offset):
        line = gf.components.rectangle(size=(length, width), layer=(1, 0), centered=False)
        line_ref = c << line
        line_ref.movey(y_offset)
        return line_ref

    # Create top section
    top_y_start = vertical_gap / 2 + section_width / 2
    for i in range(num_lines):
        y = top_y_start + i * (width + line_spacing) - section_width
        create_line(line_length, y)

    # Create bottom section
    bottom_y_start = -vertical_gap / 2 - section_width / 2
    for i in range(num_lines):
        y = bottom_y_start + i * (width + line_spacing) - section_width
        line_ref = create_line(line_length, y)
        line_ref.mirror() #Mirror each line

    # Create middle section
    middle_y_start = 0
    for i in range(num_lines):
        y = middle_y_start + i * (width + line_spacing) - section_width
        create_line(line_length, y)

    # Calculate total height
    total_height = 2 * (vertical_gap + section_width)

    # Add vertical connecting bars
    vertical_bar_width = width
    vertical_bar_length = vertical_gap + section_width + width/2 #total height

    # Top Bar
    top_vertical_bar = c << gf.components.rectangle(size=(vertical_bar_width, vertical_bar_length), layer=(1, 0), centered=True)
    top_vertical_bar.movey(vertical_gap/2 + section_width/2 -section_width)
    top_vertical_bar.movex(-line_length/2 - vertical_bar_width/2)

    #Bottom Bar
    bottom_vertical_bar = c << gf.components.rectangle(size=(vertical_bar_width, vertical_bar_length), layer=(1, 0), centered=True)
    bottom_vertical_bar.movey(-vertical_gap/2 - section_width/2 -section_width)
    bottom_vertical_bar.movex(-line_length/2 - vertical_bar_width/2)

    return c

if __name__ == "__main__":
    c = interlaced_lines(num_lines=5, line_length=50, width=2, line_spacing = 0.5, vertical_gap = 10)
    c.show()
    c.write_gds("interlaced_lines.gds")