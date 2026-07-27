import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import circle
from gdsfactory import boolean

@gf.cell
def rounded_rectangle(width: float = 10.0, height: float = 5.0, radius: float = 2.0, layer=(1, 0)):
    """Creates a rounded rectangle using boolean operations."""
    c = gf.Component()

    # Create the base rectangle
    rect = c << rectangle(size=(width, height), layer=layer, centered=True)

    # Create four circles for the rounded corners
    circle1 = c << circle(radius=radius, layer=layer)
    circle2 = c << circle(radius=radius, layer=layer)
    circle3 = c << circle(radius=radius, layer=layer)
    circle4 = c << circle(radius=radius, layer=layer)

    # Position the circles at the corners
    circle1.move((width / 2 - radius, height / 2 - radius))
    circle2.move((-width / 2 + radius, height / 2 - radius))
    circle3.move((width / 2 - radius, -height / 2 + radius))
    circle4.move((-width / 2 + radius, -height / 2 + radius))

    # Boolean OR operation to combine the rectangle and circles
    rounded_rect = boolean(rect, circle1, operation="or", layer=layer)
    rounded_rect = boolean(rounded_rect, circle2, operation="or", layer=layer)
    rounded_rect = boolean(rounded_rect, circle3, operation="or", layer=layer)
    rounded_rect = boolean(rounded_rect, circle4, operation="or", layer=layer)

    c << rounded_rect

    return c


if __name__ == "__main__":
    c = rounded_rectangle(width=10.0, height=5.0, radius=2.0)
    c.show()
    c.write_gds("rounded_rectangle.gds")