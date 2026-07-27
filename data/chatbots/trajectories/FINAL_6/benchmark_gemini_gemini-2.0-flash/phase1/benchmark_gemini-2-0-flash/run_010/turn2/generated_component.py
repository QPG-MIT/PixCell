import gdsfactory as gf
from gdsfactory.typings import LayerSpec

@gf.cell
def my_cross_with_rect(
    length: float = 4.0,
    width: float = 1.0,
    rect_length: float = 2.0,
    layer: LayerSpec = (1, 0),
) -> gf.Component:
    """
    Create a cross with a rectangle at the bottom using GDSFactory parametric functions.

    Args:
        length: length of each arm of the cross.
        width: width of each arm of the cross.
        rect_length: length of the rectangle at the bottom.
        layer: GDS layer for the cross.

    Returns:
        A GDSFactory component representing the cross with rectangle.
    """
    c = gf.Component("cross_with_rect")

    # Create the cross
    cross = c << gf.components.cross(length=length, width=width, layer=layer)

    # Create the rectangle
    rect = c << gf.components.rectangle(size=(width, rect_length), layer=layer, centered=True)
    rect.movey(-(length / 2 + rect_length / 2))  # Position the rectangle below the cross

    return c

if __name__ == "__main__":
    c = my_cross_with_rect()
    c.show()
    c.write_gds("my_cross_rect.gds")
    print(f"Device footprint: {c.bbox}")