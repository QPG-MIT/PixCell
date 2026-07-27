import gdsfactory as gf

@gf.cell
def my_device():
    c = gf.Component()
    layer = (1, 0)

    # Outer Oval
    outer_rect = c << gf.components.rectangle(size=(12, 6), layer=layer)
    outer_circle1 = c << gf.components.circle(radius=3, layer=layer)
    outer_circle2 = c << gf.components.circle(radius=3, layer=layer)
    outer_circle1.move((-6, 0))
    outer_circle2.move((6, 0))

    outer_oval = gf.boolean(outer_rect, outer_circle1, operation="or", layer=layer)
    outer_oval_ref = c << outer_oval


    # Inner Rectangle - Adjusted Size and Position
    inner_rect = c << gf.components.rectangle(size=(8, 2), layer=layer)
    inner_rect.movey(1)

    # Small rectangles between - Positions adjusted to image
    intermediate_rect1 = c << gf.components.rectangle(size=(1, 1), layer=layer)
    intermediate_rect2 = c << gf.components.rectangle(size=(1, 1), layer=layer)
    intermediate_rect1.move((-1.7, 1.5))  # Adjusted
    intermediate_rect2.move((1.7, 1.5))   # Adjusted

    # Second Inner Rectangle - Adjusted Size and Position
    inner_rect2 = c << gf.components.rectangle(size=(8, 2), layer=layer)
    inner_rect2.movey(-1) # Move down

    #Small rectangles between - Positions adjusted to image
    intermediate_rect3 = c << gf.components.rectangle(size=(1, 1), layer=layer)
    intermediate_rect4 = c << gf.components.rectangle(size=(1, 1), layer=layer)
    intermediate_rect3.move((-1.7, -0.5))  # Adjusted
    intermediate_rect4.move((1.7, -0.5))   # Adjusted

    # Trapezoid connector shapes using taper
    connector_taper1 = c << gf.components.taper(length=2, width1=0.5, width2=1, layer=layer)
    connector_taper2 = c << gf.components.taper(length=2, width1=0.5, width2=1, layer=layer)
    connector_taper1.rotate(180) #Rotate to match image.
    connector_taper1.move((-3.5, 1.5))
    connector_taper2.move((3.5-2, 1.5)) #compensate the size of taper

    connector_taper3 = c << gf.components.taper(length=2, width1=0.5, width2=1, layer=layer)
    connector_taper4 = c << gf.components.taper(length=2, width1=0.5, width2=1, layer=layer)
    connector_taper3.rotate(180) #Rotate to match image.
    connector_taper3.move((-3.5, -0.5))
    connector_taper4.move((3.5-2, -0.5)) #compensate the size of taper

    #Combine all inner shapes to intermediate_shape
    intermediate_shape = gf.Component("intermediate_shape")
    intermediate_shape << inner_rect
    intermediate_shape << intermediate_rect1
    intermediate_shape << intermediate_rect2
    intermediate_shape << inner_rect2
    intermediate_shape << intermediate_rect3
    intermediate_shape << intermediate_rect4
    intermediate_shape << connector_taper1
    intermediate_shape << connector_taper2
    intermediate_shape << connector_taper3
    intermediate_shape << connector_taper4

    intermediate_shape_ref = c << intermediate_shape


    final_shape = gf.boolean(outer_oval_ref, intermediate_shape_ref, operation="not", layer=layer)

    return final_shape

device = my_device()
device.show()
device.write_gds("my_device.gds")