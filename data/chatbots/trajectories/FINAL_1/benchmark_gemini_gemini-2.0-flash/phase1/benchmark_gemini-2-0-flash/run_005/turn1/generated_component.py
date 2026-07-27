import gdsfactory as gf
from gdsfactory.components import straight, bend_euler, taper


@gf.cell
def y_splitter(
    wg_width: float = 0.5,
    wg_length: float = 10.0,
    bend_radius: float = 10.0,
    taper_length: float = 5.0,
    gap: float = 0.5,
) -> gf.Component:
    """
    A Y-splitter component created using GDSFactory parametric functions.

    Args:
        wg_width: width of the waveguides.
        wg_length: length of the input waveguide.
        bend_radius: radius of the bends.
        taper_length: length of the tapers.
        gap: gap between the output waveguides.
    """

    c = gf.Component()

    # Cross section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0), radius=bend_radius)

    # 1. Straight waveguide (input)
    input_wg = c << straight(length=wg_length, cross_section=xs)
    c.add_port("o1", port=input_wg.ports["o1"])

    # 2. Tapers
    taper1 = c << taper(length=taper_length, width1=wg_width, width2=wg_width + gap / 2)
    taper2 = c << taper(length=taper_length, width1=wg_width, width2=wg_width + gap / 2)

    taper1.connect("o1", input_wg.ports["o2"])
    taper2.connect("o1", input_wg.ports["o2"])

    # 3. Bends
    bend1 = c << bend_euler(radius=bend_radius, angle=90, cross_section=xs)
    bend2 = c << bend_euler(radius=bend_radius, angle=-90, cross_section=xs)

    # 4. Straight waveguides (output)
    output_wg1 = c << straight(length=wg_length, cross_section=xs)
    output_wg2 = c << straight(length=wg_length, cross_section=xs)

    # Shift the components
    taper1.movey(gap / 2 + wg_width / 2 )
    bend1.movey(gap / 2 + wg_width / 2 )
    output_wg1.movey(gap / 2 + wg_width / 2 )

    taper2.movey(-gap / 2 - wg_width / 2 )
    bend2.movey(-gap / 2 - wg_width / 2 )
    output_wg2.movey(-gap / 2 - wg_width / 2)

    # 5. Connect components
    bend1.connect("o1", taper1.ports["o2"])
    output_wg1.connect("o1", bend1.ports["o2"])
    c.add_port("o2", port=output_wg1.ports["o2"])


    bend2.connect("o1", taper2.ports["o2"])
    output_wg2.connect("o1", bend2.ports["o2"])
    c.add_port("o3", port=output_wg2.ports["o2"])

    # Correct widths mismatch at connection
    taper_output_width = wg_width + gap / 2
    output_wg1.ports["o1"].width = taper_output_width
    output_wg2.ports["o1"].width = taper_output_width

    return c


if __name__ == "__main__":
    ys = y_splitter(wg_width=0.5, wg_length=10.0, bend_radius=10.0, taper_length=5.0, gap=1.0)
    ys.show()