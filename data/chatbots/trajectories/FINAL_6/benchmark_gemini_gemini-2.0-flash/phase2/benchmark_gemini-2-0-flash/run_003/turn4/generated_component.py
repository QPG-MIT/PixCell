import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.typings import LayerSpec


@gf.cell
def simple_flower(
    length: float = 4.7,
    width: float = 0.3,
    layer: LayerSpec = (1, 0),
) -> gf.Component:
    """
    Creates a simple flower shape using GDSFactory primitives, now with rectangles and ellipses for a closer match.

    Args:
        length: Total length of the cross arms.
        width: Width of the cross arms.
        layer: Layer to draw the shapes on.
    """

    c = gf.Component()

    # Calculate derived dimensions
    end_length = width  # Length of the rectangular ends
    neck_length = (length - end_length) / 2
    neck_width = width * 0.4  # Width of the "neck" connecting the end rectangle
    end_width = width *3

    # Create the rectangles for the ends of the arms
    rect1 = c << rectangle(size=(end_length, end_width), layer=layer)
    rect2 = c << rectangle(size=(end_length, end_width), layer=layer)
    rect3 = c << rectangle(size=(end_length, end_width), layer=layer)
    rect4 = c << rectangle(size=(end_length, end_width), layer=layer)


    # Position the rectangles
    rect1.center = (0, length / 2)
    rect2.center = (0, -length / 2)
    rect3.center = (length / 2, 0)
    rect4.center = (-length / 2, 0)

    neck_rect1 = c << rectangle(size=(neck_length, neck_width), layer=layer)
    neck_rect2 = c << rectangle(size=(neck_length, neck_width), layer=layer)
    neck_rect3 = c << rectangle(size=(neck_length, neck_width), layer=layer)
    neck_rect4 = c << rectangle(size=(neck_length, neck_width), layer=layer)

    neck_rect1.center = (0, length/2 - end_length/2 - neck_length/2)
    neck_rect2.center = (0, -length/2 + end_length/2 + neck_length/2)
    neck_rect3.center = (length/2 - end_length/2 - neck_length/2, 0)
    neck_rect4.center = (-length/2 + end_length/2 + neck_length/2, 0)

    return c


if __name__ == "__main__":
    c = simple_flower()
    c.show()
    c.write_gds("simple_flower.gds")