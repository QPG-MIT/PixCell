import gdsfactory as gf
from gdsfactory.components import straight, bend_circular, rectangle, mmi1x2
from gdsfactory.cross_section import strip

@gf.cell
def my_device():
    c = gf.Component("tunable_mzi")

    # Parameters
    wg_width = 0.5
    straight_length = 20
    bend_radius = 5
    heater_width = 2
    heater_length = 10
    mmi_length = 5
    heater_layer = (1,0)


    # Cross-section
    xs = strip(width=wg_width)

    # Components
    # Input and output splitters
    splitter1 = c << mmi1x2(width=wg_width, length_mmi = mmi_length, cross_section=xs)
    splitter2 = c << mmi1x2(width=wg_width, length_mmi = mmi_length, cross_section=xs)

    # Bends
    bend1 = c << bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend2 = c << bend_circular(radius=bend_radius, angle=90, cross_section=xs)
    bend3 = c << bend_circular(radius=bend_radius, angle=-90, cross_section=xs)
    bend4 = c << bend_circular(radius=bend_radius, angle=-90, cross_section=xs)

    # Straight waveguides
    upper_straight = c << straight(length=straight_length, cross_section=xs)
    lower_straight = c << straight(length=straight_length, cross_section=xs)

    # Heater
    heater = c << rectangle(size=(heater_length, heater_width), layer = heater_layer)

    # Placement

    # Place first splitter
    splitter1.move(origin=(0, 0))

    # Place bends
    bend1.connect("o1", splitter1.ports["o2"])
    bend4.connect("o1", splitter1.ports["o3"])

    # Place straights
    upper_straight.connect("o1", bend1.ports["o2"])
    lower_straight.connect("o1", bend4.ports["o2"])

    # Place other bends
    bend2.connect("o1", upper_straight.ports["o2"])
    bend3.connect("o1", lower_straight.ports["o2"])

    # Place second splitter
    splitter2.connect("o2", bend2.ports["o2"])
    splitter2.connect("o3", bend3.ports["o2"])
    splitter2.rotate(angle=180) # Correct the orientation
    splitter2.movex(splitter1.xmax + 2*bend_radius + straight_length ) #shift the entire splitter
    splitter2.movey(0)

    # Move the heater to the correct position covering the upper arm
    heater.movex(bend1.xmax + 2)
    heater.movey(bend_radius )

    # Ports
    c.add_port("o1", port=splitter1.ports["o1"])
    c.add_port("o2", port=splitter2.ports["o1"])


    c.add(heater)

    return c


if __name__ == "__main__":
    device = my_device()
    device.show()
    device.write_gds("tunable_mzi.gds")