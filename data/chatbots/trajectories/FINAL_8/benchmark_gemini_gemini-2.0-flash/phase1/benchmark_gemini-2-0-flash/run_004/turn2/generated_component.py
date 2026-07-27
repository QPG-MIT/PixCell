import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.typings import LayerSpec

@gf.cell
def rounded_rectangle_lines(
    width: float = 10.0,
    height: float = 2.0,
    spacing: float = 5.0,
    num_rectangles: int = 3,
    layer: LayerSpec = (1, 0),
    radius: float = 1.0,
) -> gf.Component:
    """
    Generates a component with rounded rectangle lines.

    Args:
        width: Width of the rectangle.
        height: Height of the rectangle.
        spacing: Spacing between the rectangles.
        num_rectangles: Number of rectangles to generate.
        layer: Layer specification for the rectangles.
        radius: Radius of the rounded corners.
    """

    c = gf.Component()

    for i in range(num_rectangles):
        y_offset = i * (height + spacing)

        # Create the rectangle
        rect = c << gf.components.rectangle(size=(width, height), layer=layer, centered=True)
        rect.movey(y_offset)

        # Add rounded corners
        bend1 = c << gf.components.bend_circular(radius=radius, angle=90, layer=layer)
        bend1.move((width/2 - radius, y_offset - height/2 + radius))

        bend2 = c << gf.components.bend_circular(radius=radius, angle=-90, layer=layer)
        bend2.move((-width/2 + radius, y_offset + height/2 - radius))

        bend3 = c << gf.components.bend_circular(radius=radius, angle=-90, layer=layer)
        bend3.move((width/2 - radius, y_offset + height/2 - radius))
        
        bend4 = c << gf.components.bend_circular(radius=radius, angle=90, layer=layer)
        bend4.move((-width/2 + radius, y_offset - height/2 + radius))
        
        c.add(bend1)
        c.add(bend2)
        c.add(bend3)
        c.add(bend4)

        r1 = c << gf.components.rectangle(size=(width - 2*radius, height), layer = layer, centered = True)
        r1.movey(y_offset)
        c.add(r1)
    
        r2 = c << gf.components.rectangle(size=(2*radius, height - 2*radius), layer = layer, centered = True)
        r2.move((width/2 - radius,y_offset))
        c.add(r2)
        
        r3 = c << gf.components.rectangle(size=(2*radius, height - 2*radius), layer = layer, centered = True)
        r3.move((-width/2 + radius,y_offset))
        c.add(r3)

    return c


if __name__ == "__main__":
    # Example usage
    c = rounded_rectangle_lines()
    c.show()
    c.write_gds("rounded_rectangle_lines.gds")