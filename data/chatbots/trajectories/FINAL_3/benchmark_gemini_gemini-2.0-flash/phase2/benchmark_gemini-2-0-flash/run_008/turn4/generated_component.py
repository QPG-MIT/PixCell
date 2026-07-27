import gdsfactory as gf

@gf.cell
def coupler_symmetric(
    bend_radius: float = 10.0,
    coupling_length: float = 20.0,
    gap: float = 0.2,
    cross_section="strip",
):
    """
    Creates a symmetric coupler-like structure with two waveguides converging and diverging.

    Args:
        bend_radius: Radius of the bends.
        coupling_length: Length of the parallel coupling section.
        gap: Gap between the waveguides in the coupling region.
        cross_section: cross section name (default: "strip")
    """
    c = gf.Component()

    # Load the cross-section
    xs = gf.get_cross_section(cross_section)

    # Create bends
    bend1 = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend2 = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend3 = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend4 = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)

    # Create straight waveguide sections
    straight1 = c << gf.components.straight(length=20, cross_section=xs)  # Input straight section
    straight2 = c << gf.components.straight(length=coupling_length, cross_section=xs)  # Coupling section
    straight3 = c << gf.components.straight(length=20, cross_section=xs)  # Output straight section

    # Create the second waveguide path (mirrored)
    straight4 = c << gf.components.straight(length=20, cross_section=xs)  # Input straight section
    straight5 = c << gf.components.straight(length=coupling_length, cross_section=xs)  # Coupling section
    straight6 = c << gf.components.straight(length=20, cross_section=xs)  # Output straight section

    # Position and connect the components for the first waveguide
    straight1.connect("o2", bend1.ports["o1"])
    bend2.connect("o1", straight2.ports["o1"])
    straight3.connect("o2", bend2.ports["o2"])
    bend1.connect("o2", straight4.ports["o1"]) #connecting the bend and the straight to create the symmetry


    # Position and connect the components for the second waveguide
    straight4.connect("o2", bend3.ports["o1"])
    bend4.connect("o1", straight5.ports["o1"])
    straight6.connect("o2", bend4.ports["o2"])


    # Move the coupling sections to create the gap
    straight2.movey(gap + xs.width)
    straight5.movey(-gap - xs.width)


    #connect bends and straights now:
    straight2.connect("o2", straight3.ports["o1"])
    straight5.connect("o2", straight6.ports["o1"])
    bend3.connect("o2",bend4.ports["o1"])



    # Add ports
    c.add_port("o1", port=straight1.ports["o1"])
    c.add_port("o2", port=straight3.ports["o1"])
    c.add_port("o3", port=straight4.ports["o1"])
    c.add_port("o4", port=straight6.ports["o1"])


    return c

if __name__ == "__main__":
    # Example usage
    component = coupler_symmetric()
    component.show()
    component.write_gds("symmetric_coupler.gds")