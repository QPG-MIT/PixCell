import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import straight

@gf.cell
def my_device():
    c = gf.Component("my_device")  # Add a name to the component

    # Parameters
    wg_width = 1.0  # Assuming 1.0 based on the scale
    top_rect_width = 20 # Width of the upper rectangle
    bottom_rect_width = 20 # Width of the bottom rectangle
    rect_height = 3 # Height of the rectangles
    
    num_lines = 5 # Number of lines in each set (from the visual)
    line_spacing = 0.5
    line_length = 20 # length of each line

    # Cross section
    # Create a new cross section instance
    xs = gf.cross_section.strip(width=wg_width)


    # Create top rectangle
    top_rect = c << rectangle(size=(top_rect_width, rect_height))
    top_rect.movey(rect_height + (num_lines-1)*line_spacing)

    # Create bottom rectangle
    bottom_rect = c << rectangle(size=(bottom_rect_width, rect_height))
    bottom_rect.movey(-(rect_height + (num_lines-1)*line_spacing))

    # Create set of straight lines above rectangle
    for i in range(num_lines):
        line = c << straight(length = line_length, cross_section=xs)
        line.movey((i+1) * line_spacing)
        line.movex(0)

    # Create set of straight lines below rectangle
    for i in range(num_lines):
        line = c << straight(length = line_length, cross_section=xs)
        line.movey(-(i+1) * line_spacing)
        line.movex(0)
        
    # Create straight lines in the middle
    for i in range(num_lines):
        line = c << straight(length = line_length, cross_section=xs)
        line.movey(i * line_spacing - 2*line_spacing) # To center them

    return c

device = my_device()
device.show()
device.write_gds("my_device.gds") # Write the GDS file