import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0)) # define cross section

    # Parameters
    wg_width = 0.5 # waveguide width
    wg_spacing = 0.5 # waveguide spacing
    num_wg = 5       # number of waveguide
    bend_radius = 10 # Bend Radius
    straight_length = 100

    straight_waveguides = []

    # Create multiple straight waveguides
    for i in range(num_wg):
        y_offset = i * (wg_width + wg_spacing)
        wg = c << gf.components.straight(length=straight_length, cross_section=xs)
        wg.movey(y_offset)
        straight_waveguides.append(wg)  # Store the waveguides

    # Create bends and connect to straight waveguides
    for i in range(num_wg):
        y_offset = i * (wg_width + wg_spacing)
        bend1 = c << gf.components.bend_euler(radius=bend_radius, cross_section=xs)
        bend2 = c << gf.components.bend_euler(radius=bend_radius, angle=-90, cross_section=xs)

        wg1 = c << gf.components.straight(length=10, cross_section=xs) # first straight section
        wg2 = c << gf.components.straight(length=10, cross_section=xs) # second straight section

        # Rotate bend2 by 180 degrees
        bend2.rotate(180)
        
        # Connect the components
        wg1.connect("o2", bend1.ports["o1"])
        bend1.connect("o2", straight_waveguides[i].ports["o1"]) # connect to the straight waveguide
        bend2.connect("o2", straight_waveguides[i].ports["o2"]) # connect to the straight waveguide
        wg2.connect("o2", bend2.ports["o1"])

        # Move to align
        bend1.movey(y_offset)
        wg1.movey(y_offset)
        bend2.movey(y_offset)
        wg2.movey(y_offset)

        # Adjust the X position of the bends, taking width into account
        wg1.movex(-straight_length/2 -10)
        bend1.movex(-straight_length/2 - bend_radius -10)
        bend2.movex(straight_length/2 + bend_radius + 10)
        wg2.movex(straight_length/2 + 10)


    return c


device = my_device()
device.show()
device.write_gds("my_device.gds")