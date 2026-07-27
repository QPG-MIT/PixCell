import gdsfactory as gf
from gdsfactory.components import bend_euler, straight


@gf.cell
def mzi():
    """Mach-Zehnder interferometer."""
    c = gf.Component("mzi")
    xs = gf.cross_section.cross_section(width=0.5)

    # Define parameters
    splitter_length = 10
    splitter_gap = 0.2
    bend_radius = 10
    arm_length = 50  # Length of each arm
    straight_length = 20

    # Add splitter
    coupler = c << gf.components.coupler_straight(
        length=splitter_length, gap=splitter_gap, cross_section=xs
    )

    # Add bends
    bend1 = c << bend_euler(radius=bend_radius, cross_section=xs)
    bend2 = c << bend_euler(radius=bend_radius, cross_section=xs)
    bend3 = c << bend_euler(radius=bend_radius, cross_section=xs)
    bend4 = c << bend_euler(radius=bend_radius, cross_section=xs)

    # Add straight arms
    arm1 = c << straight(length=arm_length, cross_section=xs)
    arm2 = c << straight(length=arm_length, cross_section=xs)
    straight1 = c << straight(length=straight_length, cross_section=xs)
    straight2 = c << straight(length=straight_length, cross_section=xs)

    # Add combiner
    coupler2 = c << gf.components.coupler_straight(
        length=splitter_length, gap=splitter_gap, cross_section=xs
    )

    #Position the objects
    dy_bend = 1  # vertical space between bends
    bend1.connect("o1", coupler.ports["o2"])
    bend2.connect("o1", coupler.ports["o3"])

    arm1.connect("o1", bend1.ports["o2"])
    arm2.connect("o1", bend2.ports["o2"])

    straight1.connect("o1", arm1.ports["o2"])
    straight2.connect("o1", arm2.ports["o2"])

    bend3.connect("o1", straight1.ports["o2"])
    bend4.connect("o1", straight2.ports["o2"])

    coupler2.connect("o2", bend3.ports["o2"])
    coupler2.connect("o3", bend4.ports["o2"])


    # Add input/output ports
    c.add_port("o1", port=coupler.ports["o1"])
    c.add_port("o2", port=coupler.ports["o4"])
    c.add_port("o3", port=coupler2.ports["o1"])
    c.add_port("o4", port=coupler2.ports["o4"])

    return c


if __name__ == "__main__":
    mzi_component = mzi()
    #mzi_component.show()  # Removed show_ports=True

    # Write the GDS file
    mzi_component.write_gds("mzi.gds")  # Specify the filename
    print("GDS file 'mzi.gds' created.")