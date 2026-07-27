import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)

    # Outer oval
    outer_rect = c << gf.components.rectangle(size=(12, 6), layer=layer)
    outer_circle1 = c << gf.components.circle(radius=3, layer=layer)
    outer_circle2 = c << gf.components.circle(radius=3, layer=layer)
    outer_circle1.move((-6, 0))
    outer_circle2.move((6, 0))

    outer_oval = gf.boolean(outer_rect, outer_circle1, operation="or", layer=layer)
    outer_oval = gf.boolean(outer_oval, outer_circle2, operation="or", layer=layer)

    # Inner Rectangle - Adjusted Size and Position
    inner_rect = c << gf.components.rectangle(size=(8, 2), layer=layer)  # Size matches diagram better
    inner_rect.movey(1) # Move up

    # Small rectangles between - Positions adjusted to image
    intermediate_rect1 = c << gf.components.rectangle(size=(1, 1), layer=layer)
    intermediate_rect2 = c << gf.components.rectangle(size=(1, 1), layer=layer)
    intermediate_rect1.move((-1.7, 1.5)) # X and Y adjusted to match image.
    intermediate_rect2.move((1.7, 1.5))  # X and Y adjusted to match image.

    # Second Inner Rectangle - Adjusted Size and Position
    inner_rect2 = c << gf.components.rectangle(size=(8, 2), layer=layer) # Size adjusted.
    inner_rect2.movey(-1) #Move Down.

    #Small rectangles between - Positions adjusted to image
    intermediate_rect3 = c << gf.components.rectangle(size=(1, 1), layer=layer)
    intermediate_rect4 = c << gf.components.rectangle(size=(1, 1), layer=layer)
    intermediate_rect3.move((-1.7, -0.5))  # X and Y adjusted to match image.
    intermediate_rect4.move((1.7, -0.5)) # X and Y adjusted to match image.

    # Connector bars - Adjusted size and positions to image
    connector_rect1 = c << gf.components.rectangle(size=(2, 0.5), layer=layer) # Size adjusted.
    connector_rect2 = c << gf.components.rectangle(size=(2, 0.5), layer=layer)  # Size adjusted.
    connector_rect1.move((-3.5, 1.5)) #Position adjusted.
    connector_rect2.move((3.5, 1.5)) #Position adjusted.

    connector_rect3 = c << gf.components.rectangle(size=(2, 0.5), layer=layer) # Size adjusted.
    connector_rect4 = c << gf.components.rectangle(size=(2, 0.5), layer=layer) # Size adjusted.
    connector_rect3.move((-3.5, -0.5)) #Position adjusted.
    connector_rect4.move((3.5, -0.5)) #Position adjusted.

    # Trapezoid connector shapes - now really trapezoids
    trapezoid_left1 = c << gf.components.rectangle(size=(1, 0.5), layer=layer)
    trapezoid_right1 = c << gf.components.rectangle(size=(1, 0.5), layer=layer)
    trapezoid_left1.move((-4.5, 1.5))
    trapezoid_right1.move((-2.5, 1.5))

    trapezoid_left2 = c << gf.components.rectangle(size=(1, 0.5), layer=layer)
    trapezoid_right2 = c << gf.components.rectangle(size=(1, 0.5), layer=layer)
    trapezoid_left2.move((2.5, 1.5))
    trapezoid_right2.move((4.5, 1.5))

    trapezoid_left3 = c << gf.components.rectangle(size=(1, 0.5), layer=layer)
    trapezoid_right3 = c << gf.components.rectangle(size=(1, 0.5), layer=layer)
    trapezoid_left3.move((-4.5, -0.5))
    trapezoid_right3.move((-2.5, -0.5))

    trapezoid_left4 = c << gf.components.rectangle(size=(1, 0.5), layer=layer)
    trapezoid_right4 = c << gf.components.rectangle(size=(1, 0.5), layer=layer)
    trapezoid_left4.move((2.5, -0.5))
    trapezoid_right4.move((4.5, -0.5))

    intermediate_shape = gf.boolean(intermediate_rect1, intermediate_rect2, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, inner_rect, operation="or", layer=layer) # Include inner rectangle
    intermediate_shape = gf.boolean(intermediate_shape, inner_rect2, operation="or", layer=layer) # Include inner rectangle
    intermediate_shape = gf.boolean(intermediate_shape, intermediate_rect3, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, intermediate_rect4, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, connector_rect1, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, connector_rect2, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, connector_rect3, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, connector_rect4, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, trapezoid_left1, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, trapezoid_right1, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, trapezoid_left2, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, trapezoid_right2, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, trapezoid_left3, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, trapezoid_right3, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, trapezoid_left4, operation="or", layer=layer)
    intermediate_shape = gf.boolean(intermediate_shape, trapezoid_right4, operation="or", layer=layer)

    final_shape = gf.boolean(outer_oval, intermediate_shape, operation="not", layer=layer)

    return final_shape

device = my_device()
device.show()
device.write_gds("my_device.gds")