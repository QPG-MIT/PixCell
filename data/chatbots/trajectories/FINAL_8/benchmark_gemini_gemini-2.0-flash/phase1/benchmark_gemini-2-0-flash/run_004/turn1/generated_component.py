import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.typings import LayerSpec

@gf.cell
def replicated_lines(
    width: float = 1.0,
    spacing: float = 0.2,
    num_lines: int = 5,
    layer: LayerSpec = (1, 0),
    single_line_length: float = 100.0,
    vertical_rise: float = 10.0,
    extension_length: float = 5.0,
) -> gf.Component:
    """
    Generates a component with replicated lines.

    Args:
        width: Width of each line.
        spacing: Spacing between lines.
        num_lines: Number of lines to generate.
        layer: Layer specification for the lines.
        single_line_length: Length of each single line segment.
        vertical_rise: Vertical rise of each side segment.
        extension_length: Straight portion length at vertical extremes
    """

    c = gf.Component()

    for i in range(num_lines):
        y_offset = i * (width + spacing)
        # Create the path for the upper lines
        p_top = gf.Path()
        p_top.append(gf.path.straight(length=extension_length))
        p_top.append(gf.path.euler(radius=vertical_rise, angle=-90))
        p_top.append(gf.path.straight(length=single_line_length))
        p_top.append(gf.path.euler(radius=vertical_rise, angle=-90))
        p_top.append(gf.path.straight(length=extension_length))

        # Extrude the path to create the waveguide
        wg_top = c << gf.path.extrude(p_top, cross_section=gf.cross_section.strip(width=width, layer=layer))
        wg_top.movey(y_offset)

        # Path for bottom
        p_bot = gf.Path()
        p_bot.append(gf.path.straight(length=extension_length))
        p_bot.append(gf.path.euler(radius=vertical_rise, angle=90))
        p_bot.append(gf.path.straight(length=single_line_length))
        p_bot.append(gf.path.euler(radius=vertical_rise, angle=90))
        p_bot.append(gf.path.straight(length=extension_length))

        # Extrude the path to create the waveguide
        wg_bot = c << gf.path.extrude(p_bot, cross_section=gf.cross_section.strip(width=width, layer=layer))
        wg_bot.movey(-y_offset)

    # Midlines - single block, easier to tweak in isolation
    for j in range(4):
        y_offset = (j * (width + spacing)) - (width + spacing)
        midline = c << rectangle(size=(single_line_length + (extension_length*2), width), layer=layer, centered=True)
        midline.movey(y_offset)

    return c


if __name__ == "__main__":
    # Example usage
    c = replicated_lines()
    c.show()
    c.write_gds("replicated_lines.gds")  # Save the GDS file