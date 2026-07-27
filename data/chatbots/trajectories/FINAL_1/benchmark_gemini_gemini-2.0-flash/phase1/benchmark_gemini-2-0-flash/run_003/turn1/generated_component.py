import gdsfactory as gf
from gdsfactory.components import taper, straight, bend_euler
from gdsfactory.cross_section import strip
from gdsfactory.path import smooth

@gf.cell
def my_splitter():
    c = gf.Component("my_splitter")

    # Parameters
    wg_width = 0.5
    taper_length = 10
    straight_length = 10
    bend_radius = 10
    gap = 0.2
    taper_width_end = wg_width + gap  # Width after taper

    # Cross section
    xs = strip(width=wg_width)
    xs_taper = strip(width=taper_width_end)

    # 1. Input Waveguide
    input_wg = c << straight(length=straight_length, cross_section=xs)

    # 2. Tapers
    taper1 = c << taper(length=taper_length, width1=wg_width, width2=taper_width_end)
    taper2 = c << taper(length=taper_length, width1=wg_width, width2=taper_width_end)
    taper1.connect("o1", input_wg.ports["o2"])
    taper2.connect("o1", input_wg.ports["o2"])  # Connects to same port as taper1 - this gets overwritten to be correctly position

    # Position taper2 relative to taper1 to be just below it.
    taper2.movey(-taper_width_end - gap) #Use the increased width for positioning

    # 3. Bends
    bend1 = c << bend_euler(radius=bend_radius, angle=90, cross_section=strip(width=taper_width_end))  # Make width consistent after taper
    bend2 = c << bend_euler(radius=bend_radius, angle=-90, cross_section=strip(width=taper_width_end))  # Flip direction for lower bend

    bend1.connect("o1", taper1.ports["o2"])
    bend2.connect("o1", taper2.ports["o2"])

    # 4. Output Straight Waveguides
    output_wg1 = c << straight(length=straight_length, cross_section=strip(width=taper_width_end)) #Consistent width for connection
    output_wg2 = c << straight(length=straight_length, cross_section=strip(width=taper_width_end))

    output_wg1.connect("o1", bend1.ports["o2"])
    output_wg2.connect("o1", bend2.ports["o2"])

    # Add ports
    c.add_port("o1", port=input_wg.ports["o1"])
    c.add_port("o2", port=output_wg1.ports["o2"])
    c.add_port("o3", port=output_wg2.ports["o2"])

    return c

if __name__ == "__main__":
    splitter = my_splitter()
    splitter.show()
    splitter.write_gds("my_splitter.gds")