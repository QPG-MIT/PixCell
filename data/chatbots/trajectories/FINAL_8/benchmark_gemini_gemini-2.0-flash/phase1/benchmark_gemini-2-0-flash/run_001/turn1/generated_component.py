import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import straight
from gdsfactory.components import bend_euler


@gf.cell
def my_device():
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=1.0, layer=(1, 0))
    gap = 1.0
    num_lines = 5
    line_length = 40
    bend_radius = 10
    offset_distance = 5

    # Top section
    top_lines = []
    for i in range(num_lines):
        line = c << straight(length=line_length, cross_section=xs)
        line.movey(i * (xs.width + gap))
        top_lines.append(line)

    top_bend = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    top_bend.connect("o1", top_lines[0].ports["o2"])  
    for i in range(1, num_lines):
      bend = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)
      bend.connect("o1", top_lines[i].ports["o2"])
      bend.movex(- (i * (xs.width + gap)))
      
    
    # Bottom section (mirror image)
    bottom_lines = []
    for i in range(num_lines):
        line = c << straight(length=line_length, cross_section=xs)
        line.movey(-i * (xs.width + gap))
        bottom_lines.append(line)
        
    bottom_bend = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bottom_bend.rotate(180)
    bottom_bend.connect("o1", bottom_lines[0].ports["o2"])  
    for i in range(1, num_lines):
      bend = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)
      bend.rotate(180)
      bend.connect("o1", bottom_lines[i].ports["o2"])
      bend.movex(- (i * (xs.width + gap)))

    # Adjust position for symmetry
    y_offset = (num_lines - 1) * (xs.width + gap) / 2
    for line in top_lines:
        line.movey(-y_offset + offset_distance)
    for line in bottom_lines:
        line.movey(y_offset - offset_distance)
        
    for i in range(1, num_lines):
      bend = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)
      bend.rotate(180)
      bend.connect("o1", bottom_lines[i].ports["o2"])
      bend.movex(- (i * (xs.width + gap)))

    top_bend.movey(offset_distance)
    bottom_bend.movey(-offset_distance)
    
    # Middle lines
    middle_lines = []
    for i in range(num_lines - 1):
        line = c << straight(length=line_length, cross_section=xs)
        line.movey((i - (num_lines -2)/2 ) * (xs.width + gap))
        middle_lines.append(line)


    return c

# Create and save
device = my_device()
device.show()
device.write_gds("my_device.gds")