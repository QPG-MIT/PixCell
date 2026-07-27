import gdsfactory as gf
from gdsfactory.components import straight, taper
from gdsfactory.cross_section import strip


@gf.cell
def my_device():
    c = gf.Component("splitter")

    # Parameters
    wg_width = 0.5
    taper_length = 10
    splitter_length = 10
    splitter_gap = 0.2
    bend_radius = 5
    output_wg_length = 5

    # Cross-section
    xs = strip(width=wg_width)

    # Straight waveguides for the splitter
    straight1 = c << straight(length=splitter_length, cross_section=xs)
    straight2 = c << straight(length=splitter_length, cross_section=xs)
    straight3 = c << straight(length=splitter_length, cross_section=xs)

    # Tapers
    taper_up = c << taper(length=taper_length, width1=wg_width, width2=wg_width)
    taper_down = c << taper(length=taper_length, width1=wg_width, width2=wg_width)


    # Bends
    bend1 = c << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend2 = c << gf.components.bend_euler(radius=bend_radius, angle=-90, cross_section=xs)


    # Output straight waveguides
    straight_out1 = c << straight(length=output_wg_length, cross_section=xs)
    straight_out2 = c << straight(length=output_wg_length, cross_section=xs)


    # Placement
    straight2.movey(wg_width / 2 + splitter_gap / 2)
    straight3.movey(-(wg_width / 2 + splitter_gap / 2))

    taper_up.connect("o1", straight2.ports["o1"])
    taper_down.connect("o1", straight3.ports["o1"])

    bend1.connect("o1", taper_up.ports["o2"])
    bend2.connect("o1", taper_down.ports["o2"])


    straight_out1.connect("o1", bend1.ports["o2"])
    straight_out2.connect("o1", bend2.ports["o2"])

    # Input Port
    c.add_port("o1", port=straight1.ports["o2"])  # Use the opposite port

    # Output Ports
    c.add_port("o2", port=straight_out1.ports["o2"])
    c.add_port("o3", port=straight_out2.ports["o2"])



    return c


if __name__ == "__main__":
    device = my_device()
    device.show()
    device.write_gds("splitter.gds")  # Save to GDS file