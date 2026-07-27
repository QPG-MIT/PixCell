import gdsfactory as gf
from gdsfactory.components import taper, straight, bend_euler
from gdsfactory.cross_section import strip
from gdsfactory.path import smooth, arc
from math import sin, pi

@gf.cell
def my_splitter():
    c = gf.Component("my_splitter")

    # Parameters
    wg_width = 0.5
    taper_length = 5
    straight_length = 5
    bend_radius = 5
    gap = 0.2
    taper_width_end = wg_width + gap
    bend_angle = 90 # Increased bend angle

    # Cross section
    xs = strip(width=wg_width)
    xs_taper = strip(width=taper_width_end)

    # 1. Input Waveguide
    input_wg = c << straight(length=straight_length, cross_section=xs)

    # Center Waveguide
    center_wg = c << straight(length=straight_length, cross_section=xs)
    center_wg.movey(0)
    input_wg.movey(0)

    # 2. Tapers
    taper1 = c << taper(length=taper_length, width1=wg_width, width2=taper_width_end)
    taper2 = c << taper(length=taper_length, width1=wg_width, width2=taper_width_end)
    taper1.connect("o1", input_wg.ports["o2"])
    taper2.connect("o1", input_wg.ports["o2"])

    # Position taper2 relative to taper1
    taper2.movey(-2*taper_width_end)

    # 3. Bends using arc path then extrude
    arc_path = arc(radius = bend_radius, angle = bend_angle)
    bend1 = c << arc_path.extrude(cross_section = strip(width = taper_width_end))
    bend2 = c << arc_path.extrude(cross_section = strip(width = taper_width_end))

    bend1.connect("o1", taper1.ports["o2"])
    bend2.connect("o1", taper2.ports["o2"])

    bend2.rotate(180)  # Rotate the second bend to make it go the correct direction

    bend2.movey(-2*bend_radius) # Reposition after rotation

    # 4. Output Straight Waveguides
    output_wg1 = c << straight(length=straight_length, cross_section=strip(width=taper_width_end))
    output_wg2 = c << straight(length=straight_length, cross_section=strip(width=taper_width_end))

    output_wg1.connect("o1", bend1.ports["o2"])
    output_wg2.connect("o1", bend2.ports["o2"])

    # Add ports
    c.add_port("o1", port=input_wg.ports["o1"])
    c.add_port("o2", port=output_wg1.ports["o2"])
    c.add_port("o3", port=output_wg2.ports["o2"])
    c.add_port("o4", port=center_wg.ports["o1"])
    c.add_port("o5", port=center_wg.ports["o2"])

    c.flatten()
    return c

if __name__ == "__main__":
    splitter = my_splitter()
    splitter.show()
    splitter.write_gds("my_splitter.gds")