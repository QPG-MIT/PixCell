import gdsfactory as gf
from gdsfactory.cross_section import strip

@gf.cell
def mach_zehnder(length=100.0, gap=0.2, bend_radius=10.0, cross_section=strip):
    """Mach-Zehnder interferometer (MZI) with straight waveguides.

    Args:
        length: length of the two parallel waveguides.
        gap: gap between the two parallel waveguides.
        bend_radius: radius of the bends.
        cross_section: cross_section to use.
    """
    c = gf.Component()
    # xs = gf.get_cross_section(cross_section)  # No longer needed as cross_section is passed directly
    width = cross_section.width
    # splitter
    splitter = c << gf.components.coupler_straight(
        length=10, gap=gap, cross_section=cross_section
    )

    # upper arm
    bend1 = c << gf.components.bend_euler(radius=bend_radius, cross_section=cross_section)
    bend2 = c << gf.components.bend_euler(radius=bend_radius, cross_section=cross_section)
    straight1 = c << gf.components.straight(length=length, cross_section=cross_section)

    # lower arm
    bend3 = c << gf.components.bend_euler(radius=bend_radius, cross_section=cross_section)
    bend4 = c << gf.components.bend_euler(radius=bend_radius, cross_section=cross_section)
    straight2 = c << gf.components.straight(length=length, cross_section=cross_section)

    # Connect splitter to upper arm
    bend1.connect("o1", splitter.ports["o2"])
    straight1.connect("o1", bend1.ports["o2"])

    # Connect splitter to lower arm
    bend3.connect("o1", splitter.ports["o3"])
    straight2.connect("o1", bend3.ports["o2"])

    # combiner
    coupler = c << gf.components.coupler_straight(
        length=10, gap=gap, cross_section=cross_section
    )
    coupler.reflect()

    # Connect upper arm to combiner
    bend2.connect("o1", straight1.ports["o2"])
    coupler.connect("o2", bend2.ports["o2"])

    # Connect lower arm to combiner
    bend4.connect("o1", straight2.ports["o2"])
    coupler.connect("o3", bend4.ports["o2"])

    # add ports
    c.add_port("o1", port=splitter.ports["o1"])
    c.add_port("o2", port=coupler.ports["o1"])

    return c

if __name__ == "__main__":
    mzi = mach_zehnder(length=100.0, gap=0.2, bend_radius=10.0, cross_section=strip)
    mzi.show(show_ports=True)
    print(mzi.size)  # Print the size of the device