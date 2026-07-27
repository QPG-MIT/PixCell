import gdsfactory as gf
from gdsfactory.components import bend_euler, straight
from gdsfactory.cross_section import strip
from gdsfactory.path import euler


@gf.cell
def capacitively_coupled_waveguide(
    wg_width: float = 0.5,
    wg_length: float = 10.0,
    gap: float = 0.2,
    bend_radius: float = 5.0,
    straight_after_bend: float = 2.0,
    layer: tuple[int, int] = (1, 0),
) -> gf.Component:
    """Creates a capacitively coupled waveguide structure.

    Args:
        wg_width: width of the waveguides.
        wg_length: length of the straight waveguide sections.
        gap: gap between the waveguides.
        bend_radius: radius of the Euler bends.
        straight_after_bend: length of the straight section after the bend.
        layer: GDS layer for the structure.

    Returns:
        A gdsfactory Component representing the structure.
    """

    c = gf.Component("capacitively_coupled_waveguide")

    # Define cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)

    # Define components
    straight_wg = straight(length=wg_length, cross_section=xs)
    bend = bend_euler(radius=bend_radius, cross_section=xs)

    # Create the top waveguide
    top_straight1 = c << straight_wg
    top_bend = c << bend
    top_straight2 = c << straight(length=straight_after_bend, cross_section=xs)

    top_bend.connect("o1", top_straight1.ports["o2"])
    top_straight2.connect("o1", top_bend.ports["o2"])

    # Create the bottom waveguide
    bottom_straight1 = c << straight_wg
    bottom_bend = c << bend
    bottom_straight2 = c << straight(length=straight_after_bend, cross_section=xs)

    bottom_straight1.connect("o1", top_straight1.ports["o1"])

    # Move bottom waveguide down by gap
    bottom_straight1.movey(-gap)
    bottom_bend.movey(-gap)
    bottom_straight2.movey(-gap)


    bottom_bend.connect("o1", bottom_straight1.ports["o2"])
    bottom_straight2.connect("o1", bottom_bend.ports["o2"])

    c.add_port("o1", port=bottom_straight1.ports["o1"])
    c.add_port("o2", port=top_straight2.ports["o2"])
    c.add_port("o3", port=bottom_straight2.ports["o2"])
    c.add_port("o4", port=top_straight1.ports["o1"])

    return c


if __name__ == "__main__":
    c = capacitively_coupled_waveguide(
        wg_length=30.0, gap=1.0, bend_radius=10.0, straight_after_bend=15.0
    )
    c.show()
    c.write_gds("capacitively_coupled_waveguide.gds")