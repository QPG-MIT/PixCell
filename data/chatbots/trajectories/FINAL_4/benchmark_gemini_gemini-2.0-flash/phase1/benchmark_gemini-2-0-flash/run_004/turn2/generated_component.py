import gdsfactory as gf
from gdsfactory.components import rectangle
import numpy as np


@gf.cell
def cusp(width=10, height=10, radius=5):
    """Creates a shape with two cusps."""
    c = gf.Component("cusp")

    # Create a rectangle
    rect = c << rectangle(size=(width, height), layer=(1, 0))
    rect.movex(-width / 2)  # Center the rectangle

    # Create two circles
    circle1 = c << gf.components.circle(radius=radius, layer=(1, 0))
    circle2 = c << gf.components.circle(radius=radius, layer=(1, 0))

    # Position the circles
    circle1.move((0, height / 2))  # Top circle
    circle2.move((0, -height / 2))  # Bottom circle

    # Boolean AND the rectangle and the two circles

    boolean_result = gf.boolean(
        rect, circle1, operation="and", layer=(1, 0)
    )
    boolean_result = gf.boolean(
        boolean_result, circle2, operation="and", layer=(1, 0)
    )

    return boolean_result


if __name__ == "__main__":
    c = cusp(width=10, height=20, radius=8)
    c.show()
    c.write_gds("cusp.gds")