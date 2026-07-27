import gdsfactory as gf
from gdsfactory.components import straight, bend_euler, taper
from gdsfactory.cross_section import strip

@gf.cell
def three_port_splitter(width=0.5, taper_length=20, bend_radius=10, gap=0.5):
    """
    Creates a three-port splitter using GDSFactory primitives.
    """
    c = gf.Component("three_port_splitter")

    # Define cross-section. Explicitly pass the width to strip
    xs = strip(width=width)

    # Create the main straight waveguide
    straight_wg = c << straight(length=taper_length, cross_section=xs)
    c.add_port("o1", port=straight_wg.ports["o1"])

    # Create the taper that splits the waveguide.  taper to width + gap/2 on either side
    taper_main = c << taper(length=taper_length, width1=width, width2=width + gap/2)

    # Connect the straight to the taper
    taper_main.connect("o1", straight_wg.ports["o2"])

    # Create two upper bends
    bend1 = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend2 = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)

    # Create two lower bends (mirrored versions)
    bend3 = c << bend_euler(radius=bend_radius, angle=-90, cross_section=xs)
    bend4 = c << bend_euler(radius=bend_radius, angle=-90, cross_section=xs)

    #Create a straight after bend for output
    straight_out1 = c << straight(length=taper_length, cross_section=xs)
    straight_out2 = c << straight(length=taper_length, cross_section=xs)

    # Position and connect first bend pair and straights
    bend1.move((taper_length, gap/2))
    bend3.move((taper_length, -gap/2))

    straight_out1.connect("o1",bend1.ports["o2"])
    straight_out2.connect("o1",bend3.ports["o2"])

    # Position and connect second bend pair. Connect to taper at midpoint.
    bend1.connect("o1", taper_main.ports["o2"])
    bend3.connect("o1", taper_main.ports["o2"])

    #Connect external ports
    c.add_port("o2", port=straight_out1.ports["o2"])
    c.add_port("o3", port=straight_out2.ports["o2"])

    return c


if __name__ == "__main__":
    splitter = three_port_splitter()
    splitter.show()  # show in klayout