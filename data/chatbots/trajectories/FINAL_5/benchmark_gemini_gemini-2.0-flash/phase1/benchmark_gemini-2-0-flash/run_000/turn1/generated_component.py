import gdsfactory as gf

@gf.cell
def device():
    c = gf.Component("my_device")

    # Define cross section
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0), radius=3.0) # Setting radius here

    # Define parameters
    length = 10.0  # Straight waveguide length
    gap = 0.2  # Gap between waveguides
    radius = 3.0  # Bend radius
    taper_length = 1.0 # Taper length at the straight sections to the bends
    extension_length = 2.0 # Length of extended tip
    straight_length_between = 3.0
    tip_width = xs.width * 0.5

    # Define elements

    # top part
    # first the tip, then the taper, the bend
    tip_top = c << gf.components.straight(length=extension_length, width=tip_width, cross_section=xs)
    taper_top = c << gf.components.taper(length=taper_length, width1=tip_width, width2=xs.width)
    bend_top = c << gf.components.bend_euler(radius=radius, angle=90, cross_section=xs)
    straight_top = c << gf.components.straight(length=straight_length_between, cross_section=xs)

    tip_top.move((0, 0)) # move the tip to the correct origin
    taper_top.connect("o1", tip_top.ports["o2"]) # attach the taper
    bend_top.connect("o1", taper_top.ports["o2"]) # attach the bend
    straight_top.connect("o1", bend_top.ports["o2"])

    # bottom part
    # first the tip, then the taper, the bend
    tip_bottom = c << gf.components.straight(length=extension_length, width=tip_width, cross_section=xs)
    taper_bottom = c << gf.components.taper(length=taper_length, width1=tip_width, width2=xs.width)
    bend_bottom = c << gf.components.bend_euler(radius=radius, angle=-90, cross_section=xs)
    straight_bottom = c << gf.components.straight(length=straight_length_between, cross_section=xs)

    tip_bottom.move((extension_length + taper_length + radius + straight_length_between, -2*radius - gap)) # move the tip to the correct origin
    taper_bottom.connect("o1", tip_bottom.ports["o2"]) # attach the taper
    bend_bottom.connect("o1", taper_bottom.ports["o2"]) # attach the bend
    straight_bottom.connect("o1", bend_bottom.ports["o2"])

    # Central part
    coupler = c << gf.components.coupler_straight(length=length, gap=gap, cross_section=xs)

    coupler.movex(extension_length + taper_length) # move the coupler x axis
    coupler.movey(-radius - gap/2.0 - xs.width/2.0) # move the coupler y axis

    # Add Ports
    c.add_port("o1", port=tip_top.ports["o1"])
    c.add_port("o2", port=tip_bottom.ports["o1"])
    c.add_port("o3", port=straight_top.ports["o2"])
    c.add_port("o4", port=straight_bottom.ports["o2"])

    return c

if __name__ == "__main__":
    d = device()
    d.show(show_ports=True)