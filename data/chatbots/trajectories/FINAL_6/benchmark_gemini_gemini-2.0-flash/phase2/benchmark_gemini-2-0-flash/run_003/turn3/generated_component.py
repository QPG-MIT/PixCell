import gdsfactory as gf
from gdsfactory.components import ellipse
from gdsfactory.typings import LayerSpec

@gf.cell
def simple_flower(
    length: float = 4.7,
    width: float = 0.3,
    layer: LayerSpec = (1, 0),
) -> gf.Component:
    """
    Creates a simple flower shape using GDSFactory primitives.

    Args:
        length: Total length of the cross arms (used as ellipse radii).
        width: Width of the cross arms (used as ellipse radii).
        layer: Layer to draw the shapes on.
    """

    c = gf.Component()

    # Define ellipse radii based on length and width
    x_radius = length / 2
    y_radius = width * 3 # Adjust this value to get the desired "petal" shape

    # Create four ellipses and rotate/position them
    ellipse1 = c << ellipse(radii=(x_radius, y_radius), layer=layer)
    ellipse1.rotate(0)
    ellipse1.center = (0, 0)

    ellipse2 = c << ellipse(radii=(x_radius, y_radius), layer=layer)
    ellipse2.rotate(90)
    ellipse2.center = (0, 0)

    ellipse3 = c << ellipse(radii=(x_radius, y_radius), layer=layer)
    ellipse3.rotate(180)
    ellipse3.center = (0, 0)

    ellipse4 = c << ellipse(radii=(x_radius, y_radius), layer=layer)
    ellipse4.rotate(270)
    ellipse4.center = (0, 0)



    return c


if __name__ == "__main__":
    c = simple_flower()
    c.show()
    c.write_gds("simple_flower.gds")