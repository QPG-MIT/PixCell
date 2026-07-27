import gdsfactory as gf
from gdsfactory.components import rectangle


@gf.cell
def my_custom_component():
    """
    Recreates the geometry from the image using GDSFactory parametric functions.
    """
    c = gf.Component("my_component")

    # Create the central shape using a cross of 2 overlapping rectangles
    horizontal_rect = rectangle(size=(3.5, 0.7), layer=(1, 0))
    vertical_rect = rectangle(size=(0.7, 3.5), layer=(1, 0))

    horizontal_ref = c << horizontal_rect
    vertical_ref = c << vertical_rect

    # Position the rectangles so they are centered on the origin
    horizontal_ref.move((-horizontal_rect.settings["size"][0] / 2, -horizontal_rect.settings["size"][1] / 2))
    vertical_ref.move((-vertical_rect.settings["size"][0] / 2, -vertical_rect.settings["size"][1] / 2))

    # Create the 4 "leaf" shapes using a combination of rectangle and offset
    leaf_width = 0.5
    leaf_length = 1.5

    leaf_horizontal_rect = rectangle(size=(leaf_length, leaf_width), layer=(1, 0))
    leaf_vertical_rect = rectangle(size=(leaf_width, leaf_length), layer=(1, 0))

    # Offset these leaf shapes by the width of the rectangles from the center
    offset_amount = 1.75
    
    horizontal_leaf_right = c << leaf_horizontal_rect
    horizontal_leaf_left = c << leaf_horizontal_rect
    vertical_leaf_top = c << leaf_vertical_rect
    vertical_leaf_bottom = c << leaf_vertical_rect

    horizontal_leaf_right.move((offset_amount - leaf_length / 2, -leaf_width / 2))
    horizontal_leaf_left.move((-offset_amount - leaf_length / 2, -leaf_width / 2))
    vertical_leaf_top.move((-leaf_width / 2, offset_amount - leaf_length / 2))
    vertical_leaf_bottom.move((-leaf_width / 2, -offset_amount - leaf_length / 2))

    return c

if __name__ == "__main__":
    component = my_custom_component()
    component.show(show_ports=True)
    # component.pprint()
    # print(component.name)