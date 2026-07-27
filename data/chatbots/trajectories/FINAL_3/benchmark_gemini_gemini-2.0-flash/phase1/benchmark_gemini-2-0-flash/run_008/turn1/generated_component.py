import gdsfactory as gf

@gf.cell
def mach_zehnder_interferometer(length_arm: float = 50.0, length_straight: float = 40.0, gap: float = 0.2, cross_section="strip"):
    """
    Mach-Zehnder Interferometer (MZI) using parametric components.

    Args:
        length_arm: Length of the MZI arm waveguides.
        length_straight: Length of the straight waveguides in the coupler.
        gap: Gap between waveguides in the coupler.
        cross_section: cross section name (default: "strip")
    """
    c = gf.Component()

    # Load the cross-section
    xs = gf.get_cross_section(cross_section)

    # Create two 50/50 couplers
    coupler1 = c << gf.components.coupler_straight(length=length_straight, gap=gap, cross_section=xs)
    coupler2 = c << gf.components.coupler_straight(length=length_straight, gap=gap, cross_section=xs)

    # Create arm waveguides
    arm1 = c << gf.components.straight(length=length_arm, cross_section=xs)
    arm2 = c << gf.components.straight(length=length_arm, cross_section=xs)

    # Create bends
    bend1 = c << gf.components.bend_euler(cross_section=xs)
    bend2 = c << gf.components.bend_euler(cross_section=xs)
    bend3 = c << gf.components.bend_euler(cross_section=xs)
    bend4 = c << gf.components.bend_euler(cross_section=xs)

    # Position components
    coupler2.move((length_straight + 2*length_arm, 0))

    # Connect the first coupler
    bend1.connect("o1", coupler1.ports["o2"])
    bend2.connect("o1", coupler1.ports["o3"])

    # Connect the arms with the coupler
    arm1.connect("o1", bend1.ports["o2"])
    arm2.connect("o1", bend2.ports["o2"])

    bend3.connect("o2", coupler2.ports["o2"])
    bend4.connect("o2", coupler2.ports["o3"])

    bend3.connect("o1", arm1.ports["o2"])
    bend4.connect("o1", arm2.ports["o2"])


    # Add ports
    c.add_port("o1", port=coupler1.ports["o1"])
    c.add_port("o2", port=coupler1.ports["o4"])
    c.add_port("o3", port=coupler2.ports["o1"])
    c.add_port("o4", port=coupler2.ports["o4"])

    return c

if __name__ == "__main__":
    # Example usage
    mzi = mach_zehnder_interferometer()
    mzi.show()
    mzi.write_gds("mzi.gds")  # Save to GDS file if needed