import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()

    xs = gf.cross_section.cross_section(width=1, layer=(1, 0))  # Adjust width as needed

    # Constants - adjust according to your analysis of the image
    vspacing = 1 #vertical spacing between lines
    num_lines = 5 #number of lines in each group
    large_length = 60  #length of large section
    small_length = 30 #length of small section
    vertical_length = 5 # vertical length of vertical sections

    # Helper function to make a block of parallel lines
    def line_block(length, num_lines, vspacing):
        block = gf.Component()
        for i in range(num_lines):
            wg = block << gf.components.straight(length=length, cross_section=xs)
            wg.movey(i * vspacing)
        
        # Find the total height of the block and center it around (0,0)
        total_height = (num_lines - 1) * vspacing
        block.move((-length/2, -total_height/2))

        return block

    # Create upper lines
    upper_lines = c << line_block(large_length, num_lines, vspacing)
    upper_lines.movey(2*vspacing + vertical_length)
    # Create lower lines
    lower_lines = c << line_block(large_length, num_lines, vspacing)
    lower_lines.movey(-(2*vspacing + vertical_length))
    # Create center lines
    center_lines = c << line_block(small_length, num_lines, vspacing)

    # Create vertical sections using paths

    path_upper = gf.Path()
    path_upper.append(gf.path.straight(vertical_length))

    path_lower = gf.Path()
    path_lower.append(gf.path.straight(vertical_length))

    # Extrude the paths
    def vertical_line_block(path, num_lines, vspacing):
        block = gf.Component()
        for i in range(num_lines):
            vert_section = block << gf.path.extrude(path, cross_section=xs)
            vert_section.movey(i * vspacing)
        
        total_height = (num_lines - 1) * vspacing
        block.move((0, -total_height/2))

        return block

    upper_left_vertical_section = c << vertical_line_block(path_upper, num_lines, vspacing)
    upper_left_vertical_section.rotate(-90)
    upper_left_vertical_section.move((-(large_length/2), 2*vspacing + vertical_length + (num_lines-1)*vspacing/2))

    upper_right_vertical_section = c << vertical_line_block(path_upper, num_lines, vspacing)
    upper_right_vertical_section.rotate(90)
    upper_right_vertical_section.move(((large_length/2), 2*vspacing + vertical_length + (num_lines-1)*vspacing/2))

    lower_left_vertical_section = c << vertical_line_block(path_lower, num_lines, vspacing)
    lower_left_vertical_section.rotate(-90)
    lower_left_vertical_section.move((-(large_length/2), - (2*vspacing + vertical_length + (num_lines-1)*vspacing/2)))

    lower_right_vertical_section = c << vertical_line_block(path_lower, num_lines, vspacing)
    lower_right_vertical_section.rotate(90)
    lower_right_vertical_section.move(((large_length/2), - (2*vspacing + vertical_length + (num_lines-1)*vspacing/2)))

    # Overall Device Size - Adjusted footprint (120.0, 4.0)
    c.add_ports(c.get_ports_list())
    return c

device = my_device()
device.show() # Removed show_ports=True
device.write_gds("my_device.gds")