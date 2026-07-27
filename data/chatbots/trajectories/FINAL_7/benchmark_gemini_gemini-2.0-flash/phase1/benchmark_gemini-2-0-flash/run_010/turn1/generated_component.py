import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.difftest import difftest

@gf.cell
def racetrack_resonator_with_blocks():
    """Racetrack resonator with blocks inside."""
    c = gf.Component()
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius=10.0)
    
    # Outer racetrack
    # straight section
    straight_length = 3.0
    straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    # bend section
    radius = 10.0
    bend = c << gf.components.bend_circular(radius=radius, angle=180, cross_section=xs)
    
    # Place and connect outer race track
    bend1 = c << gf.components.bend_circular(radius=radius, angle=180, cross_section=xs)
    bend2 = c << gf.components.bend_circular(radius=radius, angle=180, cross_section=xs)

    straight1 = c << gf.components.straight(length=straight_length, cross_section=xs)
    straight2 = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    bend1.connect("o1", straight1.ports["o2"])
    bend2.connect("o1", straight2.ports["o2"])
    straight2.connect("o1", bend1.ports["o2"])
    straight1.movey(2*radius+2*xs.width)
    straight2.movey(2*radius+2*xs.width)

    # Create a larger racetrack (same size)
    outer_track_width = 0.6
    straight_outer = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    # bend section
    bend_outer = c << gf.components.bend_circular(radius=radius, angle=180, cross_section=xs)
    
    # Place and connect outer race track
    bend1_outer = c << gf.components.bend_circular(radius=radius, angle=180, cross_section=xs)
    bend2_outer = c << gf.components.bend_circular(radius=radius, angle=180, cross_section=xs)

    straight1_outer = c << gf.components.straight(length=straight_length, cross_section=xs)
    straight2_outer = c << gf.components.straight(length=straight_length, cross_section=xs)
    
    bend1_outer.connect("o1", straight1_outer.ports["o2"])
    bend2_outer.connect("o1", straight2_outer.ports["o2"])
    straight2_outer.connect("o1", bend1_outer.ports["o2"])
    straight1_outer.movey(2*radius+2*xs.width +outer_track_width)
    straight2_outer.movey(2*radius+2*xs.width +outer_track_width)

    
    inner_track = gf.boolean(straight1, straight1_outer, operation="not", layer=(1, 0))
    c << inner_track
    inner_track2 = gf.boolean(straight2, straight2_outer, operation="not", layer=(1, 0))
    c << inner_track2

    inner_bend1 = gf.boolean(bend1, bend1_outer, operation="not", layer=(1, 0))
    c << inner_bend1

    inner_bend2 = gf.boolean(bend2, bend2_outer, operation="not", layer=(1, 0))
    c << inner_bend2
    
    # Rectangle Blocks
    block_width = 0.4
    block_height = 0.2
    
    # Upper blocks
    block1 = c << rectangle(size=(block_width, block_height), layer=(1, 0), centered=True)
    block2 = c << rectangle(size=(block_width, block_height), layer=(1, 0), centered=True)
    
    block1_x_offset = -block_width*0.7
    block1_y_offset = 2*radius + 2*xs.width+outer_track_width/2.0
    block1.move((block1_x_offset, block1_y_offset))

    block2_x_offset = block_width*0.7
    block2_y_offset = 2*radius + 2*xs.width+outer_track_width/2.0
    block2.move((block2_x_offset, block2_y_offset))

    # Lower blocks
    block3 = c << rectangle(size=(block_width, block_height), layer=(1, 0), centered=True)
    block4 = c << rectangle(size=(block_width, block_height), layer=(1, 0), centered=True)

    block3_x_offset = -block_width*0.7
    block3_y_offset = outer_track_width/2.0
    block3.move((block3_x_offset, block3_y_offset))

    block4_x_offset = block_width*0.7
    block4_y_offset = outer_track_width/2.0
    block4.move((block4_x_offset, block4_y_offset))
    
    return c

if __name__ == "__main__":
    c = racetrack_resonator_with_blocks()
    c.show(show_ports=True)
    difftest(c)