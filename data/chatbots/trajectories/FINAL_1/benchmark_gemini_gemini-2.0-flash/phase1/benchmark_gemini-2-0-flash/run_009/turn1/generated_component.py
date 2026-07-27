import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.cross_section import strip

@gf.cell
def y_splitter(
    wg_width: float = 0.5,
    wg_length: float = 20.0,
    taper_length: float = 10.0,
    bend_radius: float = 5.0,
    gap: float = 0.2,
) -> Component:
    """
    Recreates the Y-splitter geometry from the provided image using GDSFactory.

    Args:
        wg_width: Width of the input/output waveguides.
        wg_length: Length of the input and output waveguides.
        taper_length: Length of the tapers.
        bend_radius: Radius of the bends.
        gap: Gap between the output waveguides.

    Returns:
        A GDSFactory Component representing the Y-splitter.
    """
    c = gf.Component("y_splitter")

    # Define the cross-section for the waveguides
    xs = strip(width=wg_width)

    # Input waveguide
    input_wg = c << gf.components.straight(length=wg_length, cross_section=xs)

    # Tapers
    taper_top = c << gf.components.taper(
        length=taper_length, width1=wg_width, width2=wg_width + gap / 2, cross_section=xs
    )
    taper_bottom = c << gf.components.taper(
        length=taper_length, width1=wg_width, width2=wg_width + gap / 2, cross_section=xs
    )

    # Bends
    bend_top = c << gf.components.bend_euler(radius=bend_radius, cross_section=xs)
    bend_bottom = c << gf.components.bend_euler(radius=bend_radius, cross_section=xs)

    # Output waveguides
    output_wg_top = c << gf.components.straight(length=wg_length, cross_section=xs)
    output_wg_bottom = c << gf.components.straight(
        length=wg_length, cross_section=xs
    )

    # Connect input waveguide to tapers
    taper_top.connect("o1", input_wg.ports["o2"])
    taper_bottom.connect("o1", input_wg.ports["o2"])

    # Position tapers vertically
    taper_top.movey(gap / 2)
    taper_bottom.movey(-gap / 2)

    # Connect tapers to bends
    bend_top.connect("o1", taper_top.ports["o2"])
    bend_bottom.connect("o1", taper_bottom.ports["o2"])

    # Rotate bends
    bend_top.rotate(90)
    bend_bottom.rotate(-90)

    # Connect bends to output waveguides
    output_wg_top.connect("o1", bend_top.ports["o2"])
    output_wg_bottom.connect("o1", bend_bottom.ports["o2"])

    # Add ports
    c.add_port("o1", port=input_wg.ports["o1"])
    c.add_port("o2", port=output_wg_top.ports["o2"])
    c.add_port("o3", port=output_wg_bottom.ports["o2"])

    return c

if __name__ == "__main__":
    c = y_splitter()
    c.show(show_ports=True)