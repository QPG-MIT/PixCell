import gdsfactory as gf
from gdsfactory.typings import component

@gf.cell
def my_device() -> component:
    """Recreates the geometry from the attached PNG using GDSFactory parametric functions."""
    c = gf.Component("my_device")

    # Define cross-section (waveguide)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius=10)
    
    # Parameters (adjust based on the image)
    straight_length_short = 10
    straight_length_long = 20
    bend_radius = 10  # Assume bends are circular, adjust as needed.

    # Top part
    # Horizontal lines
    straight1 = c << gf.components.straight(length=straight_length_long, cross_section=xs)
    straight2 = c << gf.components.straight(length=straight_length_long, cross_section=xs)
    straight3 = c << gf.components.straight(length=straight_length_long, cross_section=xs)
    straight4 = c << gf.components.straight(length=straight_length_long, cross_section=xs)

    straight2.movey(xs.width * 1.5)
    straight3.movey(xs.width * 3)
    straight4.movey(xs.width * 4.5)

    # Bends
    bend1_top_left = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend1_top_right = c << gf.components.bend_circular(radius=bend_radius, angle=-90, cross_section=xs) # Use negative angle for the other direction
    bend2_top_left = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend2_top_right = c << gf.components.bend_circular(radius=bend_radius, angle=-90, cross_section=xs)
    bend3_top_left = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend3_top_right = c << gf.components.bend_circular(radius=bend_radius, angle=-90, cross_section=xs)
    bend4_top_left = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend4_top_right = c << gf.components.bend_circular(radius=bend_radius, angle=-90, cross_section=xs)
    
    bend1_top_left.connect("o1", straight1.ports["o1"])
    bend1_top_right.connect("o1", straight1.ports["o2"])
    bend2_top_left.connect("o1", straight2.ports["o1"])
    bend2_top_right.connect("o1", straight2.ports["o2"])
    bend3_top_left.connect("o1", straight3.ports["o1"])
    bend3_top_right.connect("o1", straight3.ports["o2"])
    bend4_top_left.connect("o1", straight4.ports["o1"])
    bend4_top_right.connect("o1", straight4.ports["o2"])

    straight_connector_top_left = c << gf.components.straight(length=straight_length_short, cross_section=xs)
    straight_connector_top_right = c << gf.components.straight(length=straight_length_short, cross_section=xs)

    straight_connector_top_left.connect("o1", bend4_top_left.ports["o2"])
    straight_connector_top_right.connect("o1", bend4_top_right.ports["o2"])

    top_center_y = straight3.center[1]
    top_center_x = (straight_connector_top_left.center[0] + straight_connector_top_right.center[0])/2

    # Center lines
    straight_center1 = c << gf.components.straight(length=straight_length_long*2, cross_section=xs)
    straight_center2 = c << gf.components.straight(length=straight_length_long*2, cross_section=xs)
    straight_center3 = c << gf.components.straight(length=straight_length_long*2, cross_section=xs)
    straight_center4 = c << gf.components.straight(length=straight_length_long*2, cross_section=xs)

    straight_center1.movey(-xs.width * 7)
    straight_center2.movey(-xs.width * 8.5)
    straight_center3.movey(-xs.width * 10)
    straight_center4.movey(-xs.width * 11.5)

    straight_center1.movex(top_center_x - straight_center1.center[0])
    straight_center2.movex(top_center_x - straight_center2.center[0])
    straight_center3.movex(top_center_x - straight_center3.center[0])
    straight_center4.movex(top_center_x - straight_center4.center[0])

    # Bottom Part
    straight_bottom1 = c << gf.components.straight(length=straight_length_long, cross_section=xs)
    straight_bottom2 = c << gf.components.straight(length=straight_length_long, cross_section=xs)
    straight_bottom3 = c << gf.components.straight(length=straight_length_long, cross_section=xs)
    straight_bottom4 = c << gf.components.straight(length=straight_length_long, cross_section=xs)

    straight_bottom1.movey(-xs.width * 14)
    straight_bottom2.movey(-xs.width * 15.5)
    straight_bottom3.movey(-xs.width * 17)
    straight_bottom4.movey(-xs.width * 18.5)

    straight_bottom1.movex(top_center_x - straight_bottom1.center[0])
    straight_bottom2.movex(top_center_x - straight_bottom2.center[0])
    straight_bottom3.movex(top_center_x - straight_bottom3.center[0])
    straight_bottom4.movex(top_center_x - straight_bottom4.center[0])

    # Bends
    bend1_bottom_left = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend1_bottom_right = c << gf.components.bend_circular(radius=bend_radius, angle=-90, cross_section=xs)
    bend2_bottom_left = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend2_bottom_right = c << gf.components.bend_circular(radius=bend_radius, angle=-90, cross_section=xs)
    bend3_bottom_left = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend3_bottom_right = c << gf.components.bend_circular(radius=bend_radius, angle=-90, cross_section=xs)
    bend4_bottom_left = c << gf.components.bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend4_bottom_right = c << gf.components.bend_circular(radius=bend_radius, angle=-90, cross_section=xs)

    bend1_bottom_left.connect("o2", straight_bottom1.ports["o1"])
    bend1_bottom_right.connect("o2", straight_bottom1.ports["o2"])
    bend2_bottom_left.connect("o2", straight_bottom2.ports["o1"])
    bend2_bottom_right.connect("o2", straight_bottom2.ports["o2"])
    bend3_bottom_left.connect("o2", straight_bottom3.ports["o1"])
    bend3_bottom_right.connect("o2", straight_bottom3.ports["o2"])
    bend4_bottom_left.connect("o2", straight_bottom4.ports["o1"])
    bend4_bottom_right.connect("o2", straight_bottom4.ports["o2"])

    straight_connector_bottom_left = c << gf.components.straight(length=straight_length_short, cross_section=xs)
    straight_connector_bottom_right = c << gf.components.straight(length=straight_length_short, cross_section=xs)

    straight_connector_bottom_left.connect("o2", bend1_bottom_left.ports["o1"])
    straight_connector_bottom_right.connect("o2", bend1_bottom_right.ports["o1"])

    # Move the component to origin (0,0)
    c.center = (0,0)

    return c

if __name__ == "__main__":
    device = my_device()
    device.show(show_ports=True)  # Show in klayout
    device.write_gds("my_device.gds")