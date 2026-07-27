import gdsfactory as gf
from gdsfactory.components import bend_euler, straight, coupler_straight
from gdsfactory.cross_section import strip


@gf.cell
def mach_zehnder_interferometer(
    length_arm: float = 50.0,
    length_straight: float = 10.0,
    gap: float = 0.2,
    bend_radius: float = 10.0,
    cross_section=strip(),  # Instantiate the cross_section
) -> gf.Component:
    """
    Mach-Zehnder interferometer (MZI).

    Args:
        length_arm: length of the MZI arms.
        length_straight: length of the straight sections between the bends.
        gap: gap between the two arms.
        bend_radius: radius of the bends.
        cross_section: cross-section of the waveguides.

    """
    c = gf.Component()
    width = cross_section.width

    # splitter
    splitter = c << coupler_straight(
        length=length_straight, gap=gap, cross_section=cross_section
    )

    # upper arm
    bend1 = c << bend_euler(radius=bend_radius, cross_section=cross_section)
    bend1.connect("o1", splitter.ports["o1"])

    straight1 = c << straight(length=length_arm, cross_section=cross_section)
    straight1.connect("o1", bend1.ports["o2"])

    bend2 = c << bend_euler(radius=bend_radius, angle=-90, cross_section=cross_section)
    bend2.connect("o1", straight1.ports["o2"])

    # lower arm
    bend3 = c << bend_euler(radius=bend_radius, angle=180, cross_section=cross_section)
    bend3.connect("o1", splitter.ports["o4"])

    straight2 = c << straight(length=length_arm, cross_section=cross_section)
    straight2.connect("o1", bend3.ports["o2"])

    bend4 = c << bend_euler(radius=bend_radius, angle=-90, cross_section=cross_section)
    bend4.connect("o1", straight2.ports["o2"])

    # combiner
    combiner = c << coupler_straight(
        length=length_straight, gap=gap, cross_section=cross_section
    )
    combiner.connect("o1", bend2.ports["o2"])
    combiner.connect("o4", bend4.ports["o2"])

    c.add_port("o1", port=splitter.ports["o2"])
    c.add_port("o2", port=splitter.ports["o3"])
    c.add_port("o3", port=combiner.ports["o2"])
    c.add_port("o4", port=combiner.ports["o3"])

    return c


if __name__ == "__main__":
    mzi = mach_zehnder_interferometer(
        length_arm=50, length_straight=10, gap=0.2, bend_radius=10
    )
    mzi.show(show_ports=True)