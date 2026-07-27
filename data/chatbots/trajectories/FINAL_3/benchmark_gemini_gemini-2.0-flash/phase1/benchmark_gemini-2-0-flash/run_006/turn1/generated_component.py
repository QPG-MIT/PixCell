import gdsfactory as gf

@gf.cell
def mach_zehnder_interferometer():
    """
    Recreates a Mach-Zehnder Interferometer using GDSFactory.
    """
    c = gf.Component("mach_zehnder_interferometer")

    # Define the cross-section for the waveguides
    xs = gf.cross_section.cross_section(width=1, layer=(1, 0))  # Example cross-section

    # 1. Input and Output Straight Waveguides
    straight_length = 20  # Adjust as needed
    input_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    output_straight = c << gf.components.straight(length=straight_length, cross_section=xs)
    output_straight.move((2*straight_length, 0))

    # 2. Y-Splitter/Combiner (using a directional coupler)
    coupler_length = 30 # Adjust as needed
    coupler_gap = 0.5  # Adjust as needed

    coupler1 = c << gf.components.coupler_straight(length=coupler_length, gap=coupler_gap, cross_section=xs)
    coupler1.move((straight_length, -0.5*(2*straight_length+coupler_length+1)))


    coupler2 = c << gf.components.coupler_straight(length=coupler_length, gap=coupler_gap, cross_section=xs)
    coupler2.move((straight_length, +0.5*(2*straight_length+coupler_length+1)))
    coupler2.rotate(180)

    #connect the straights with the couplers
    input_straight_bend_top = c << gf.components.bend_euler(radius=30, angle=90, cross_section=xs)
    input_straight_bend_bot = c << gf.components.bend_euler(radius=30, angle=-90, cross_section=xs)
    
    input_straight_bend_top.connect("o1", input_straight.ports["o2"])
    input_straight_bend_bot.connect("o1", input_straight.ports["o2"])

    coupler1.connect("o1", input_straight_bend_top.ports["o2"])
    coupler2.connect("o1", input_straight_bend_bot.ports["o2"])

    # Output Straights
    output_straight_bend_top = c << gf.components.bend_euler(radius=30, angle=-90, cross_section=xs)
    output_straight_bend_bot = c << gf.components.bend_euler(radius=30, angle=90, cross_section=xs)

    output_straight_bend_top.connect("o1", output_straight.ports["o1"])
    output_straight_bend_bot.connect("o1", output_straight.ports["o1"])

    coupler1.connect("o2", output_straight_bend_top.ports["o2"])
    coupler2.connect("o2", output_straight_bend_bot.ports["o2"])

    # Add ports
    c.add_port("o1", port=input_straight.ports["o1"])
    c.add_port("o2", port=output_straight.ports["o2"])

    return c

if __name__ == "__main__":
    mzi = mach_zehnder_interferometer()
    mzi.show() # Removed show_ports=True

    # Verify device footprint constraints
    footprint = mzi.bbox
    print(f"Device footprint: {footprint[2]:.2f} x {footprint[3]:.2f} um")