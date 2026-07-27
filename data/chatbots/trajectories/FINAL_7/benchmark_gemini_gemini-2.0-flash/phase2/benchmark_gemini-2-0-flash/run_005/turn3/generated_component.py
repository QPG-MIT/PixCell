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

    #c << rounded_rect  # Removed: We need to boolean this shape

    return rounded_rect  # Return the rounded_rect Component


@gf.cell
def target_shape(
    width: float = 10.0,
    height: float = 5.0,
    radius: float = 2.0,
    capsule_width: float = 1.0,
    capsule_length: float = 4.0,
    capsule_spacing: float = 1.0,
    layer=(1, 0),
):
    """Creates the target shape."""
    c = gf.Component()

    # Create the outer rounded rectangle
    outer_rect = c << rounded_rectangle(width=width, height=height, radius=radius, layer=layer)

    # Create the first capsule
    capsule1_rect = rectangle(size=(capsule_length, capsule_width), layer=layer, centered=True)
    capsule1_circle1 = circle(radius=capsule_width / 2, layer=layer)
    capsule1_circle2 = circle(radius=capsule_width / 2, layer=layer)
    capsule1 = gf.Component("capsule1")
    r1 = capsule1 << capsule1_rect
    c1 = capsule1 << capsule1_circle1
    c2 = capsule1 << capsule1_circle2
    c1.move((-capsule_length/2,0))
    c2.move((capsule_length/2, 0))
    capsule1_polygon = boolean(capsule1_rect, capsule1_circle1, operation="or", layer=layer)
    capsule1_polygon = boolean(capsule1_polygon, capsule1_circle2, operation="or", layer=layer)

    capsule1_ref = c << capsule1_polygon

    # Create the second capsule
    capsule2_rect = rectangle(size=(capsule_length, capsule_width), layer=layer, centered=True)
    capsule2_circle1 = circle(radius=capsule_width / 2, layer=layer)
    capsule2_circle2 = circle(radius=capsule_width / 2, layer=layer)
    capsule2 = gf.Component("capsule2")
    r2 = capsule2 << capsule2_rect
    c3 = capsule2 << capsule2_circle1
    c4 = capsule2 << capsule2_circle2
    c3.move((-capsule_length/2,0))
    c4.move((capsule_length/2, 0))
    capsule2_polygon = boolean(capsule2_rect, capsule2_circle1, operation="or", layer=layer)
    capsule2_polygon = boolean(capsule2_polygon, capsule2_circle2, operation="or", layer=layer)

    capsule2_ref = c << capsule2_polygon
    # Position the capsules
    y_offset = (capsule_spacing + capsule_width) / 2
    capsule1_ref.move((0, y_offset))
    capsule2_ref.move((0, -y_offset))

    # Boolean subtraction
    intermediate_shape = boolean(outer_rect, capsule1_ref, operation="not", layer=layer)
    final_shape = boolean(intermediate_shape, capsule2_ref, operation="not", layer=layer)

    c << final_shape

    return c


if __name__ == "__main__":
    c = target_shape(width=10.0, height=5.0, radius=2.0)
    c.show()
    c.write_gds("target_shape.gds")