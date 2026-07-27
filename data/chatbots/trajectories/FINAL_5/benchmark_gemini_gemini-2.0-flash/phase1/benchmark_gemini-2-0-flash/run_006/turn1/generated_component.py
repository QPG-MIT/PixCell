import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()

    # Cross-section definition
    xs = gf.cross_section.cross_section(width=0.25, layer=(1, 0), radius=10) # Adjust width as needed
    
    # Constants
    length_straight = 3 # Adjust to fit
    gap_center = 0.1 # Adjust to fit
    bend_radius = 10 # min radius
    gap_coupler = 0.1
    length_coupler = 1.5
    num_teeth = 50 # approximate
    width_teeth = 0.02  # Estimated based on density in the image
    gap_teeth = 0.02  # Estimated based on density in the image
    length_teeth = num_teeth * (width_teeth + gap_teeth) 
    
    # Central waveguide structure
    straight_center = c << gf.components.straight(length=length_teeth, cross_section=xs)
    straight_center.movey(0)

    straight_center_top = c << gf.components.straight(length=length_straight, cross_section=xs)
    straight_center_top.movey(gap_center)
    
    # Upper U-shaped waveguide
    bend_top_left = c << gf.components.bend_euler(radius=bend_radius, angle=-90, cross_section=xs)
    bend_top_left.connect("o1", straight_center.ports["o2"])

    bend_top_right = c << gf.components.bend_euler(radius=bend_radius, angle=-90, cross_section=xs)
    bend_top_right.connect("o1", straight_center.ports["o1"])


    straight_top = c << gf.components.straight(length=length_coupler, cross_section=xs)
    straight_top.connect("o1", bend_top_left.ports["o2"])

    straight_top2 = c << gf.components.straight(length=length_coupler, cross_section=xs)
    straight_top2.connect("o1", bend_top_right.ports["o2"])

    bend_top_right2 = c << gf.components.bend_euler(radius=bend_radius, angle=-90, cross_section=xs)
    bend_top_right2.connect("o1", straight_top2.ports["o2"])

    bend_top_left2 = c << gf.components.bend_euler(radius=bend_radius, angle=-90, cross_section=xs)
    bend_top_left2.connect("o1", straight_top.ports["o2"])

    straight_top_out = c << gf.components.straight(length=2, cross_section=xs)
    straight_top_out.connect("o1", bend_top_left2.ports["o2"])

    straight_top_out2 = c << gf.components.straight(length=2, cross_section=xs)
    straight_top_out2.connect("o1", bend_top_right2.ports["o2"])

    # Lower U-shaped waveguide
    bend_bottom_left = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend_bottom_left.connect("o1", straight_center.ports["o2"])
    bend_bottom_left.movey(-2 * gap_center)

    bend_bottom_right = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend_bottom_right.connect("o1", straight_center.ports["o1"])
    bend_bottom_right.movey(-2 * gap_center)

    straight_bottom = c << gf.components.straight(length=length_coupler, cross_section=xs)
    straight_bottom.connect("o1", bend_bottom_left.ports["o2"])

    straight_bottom2 = c << gf.components.straight(length=length_coupler, cross_section=xs)
    straight_bottom2.connect("o1", bend_bottom_right.ports["o2"])

    bend_bottom_right2 = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend_bottom_right2.connect("o1", straight_bottom2.ports["o2"])

    bend_bottom_left2 = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend_bottom_left2.connect("o1", straight_bottom.ports["o2"])

    straight_bottom_out = c << gf.components.straight(length=2, cross_section=xs)
    straight_bottom_out.connect("o1", bend_bottom_left2.ports["o2"])

    straight_bottom_out2 = c << gf.components.straight(length=2, cross_section=xs)
    straight_bottom_out2.connect("o1", bend_bottom_right2.ports["o2"])

    # Central Teeth - using rectangle array

    tooth = gf.components.rectangle(size=(width_teeth, 0.25), layer=(1, 0), centered=True)  # Tooth dimension

    tooth_array = c << gf.components.array(tooth, columns=num_teeth, rows=1, spacing=(width_teeth + gap_teeth, 0))
    tooth_array.movex(-length_teeth/2 + width_teeth/2)
    tooth_array.movey(gap_center /2)

    tooth_array_bottom = c << gf.components.array(tooth, columns=num_teeth, rows=1, spacing=(width_teeth + gap_teeth, 0))
    tooth_array_bottom.movex(-length_teeth/2 + width_teeth/2)
    tooth_array_bottom.movey(- 1.5 * gap_center)


    # Add Ports (Define based on final layout)

    c.add_port("o1", port=straight_top_out.ports["o2"])
    c.add_port("o2", port=straight_top_out2.ports["o2"])
    c.add_port("o3", port=straight_bottom_out.ports["o2"])
    c.add_port("o4", port=straight_bottom_out2.ports["o2"])


    return c

device = my_device()
device.show(show_ports=True)