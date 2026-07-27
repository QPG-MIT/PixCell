import gdsfactory as gf
from gdsfactory.components import rectangle, ellipse

@gf.cell
def my_fancy_cross(length=2.5, width=0.5, end_width=0.1):
    """
    Creates a cross geometry with rounded elements at the end of each arm,
    resembling a four-leaf clover or asterisk-like shape.
    """
    c = gf.Component("my_fancy_cross")

    # Define the layers
    layer = (1, 0)

    # Create the central rectangles
    horizontal_rect = c << rectangle(size=(length*2, width), layer=layer, centered=True)
    vertical_rect = c << rectangle(size=(width, length*2), layer=layer, centered=True)

    # Create the rounded ends for each arm
    ellipse_params = {'radii': (end_width*2, length*2), 'layer': layer}
    horizontal_left = c << ellipse(**ellipse_params)
    horizontal_left.move((-length*2,0))

    horizontal_right = c << ellipse(**ellipse_params)
    horizontal_right.move((length*2,0))

    vertical_top = c << ellipse(**ellipse_params)
    vertical_top.move((0,length*2))
    vertical_top.rotate(90)

    vertical_bottom = c << ellipse(**ellipse_params)
    vertical_bottom.move((0,-length*2))
    vertical_bottom.rotate(90)

    return c

if __name__ == "__main__":
    c = my_fancy_cross()
    c.show()  # Show in KLayout
    c.write_gds("my_fancy_cross.gds")  # Save as GDS file