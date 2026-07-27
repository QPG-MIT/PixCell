import gdsfactory as gf
from gdsfactory.components import rectangle, cross

@gf.cell
def my_flower_cross(length=4.7, width=0.75, stem_length=0.75):
    """
    Recreates the flower cross geometry using GDSFactory primitives and boolean operations.
    """
    c = gf.Component("my_flower_cross")  # Name the component

    # Create rounded rectangles representing the petals
    petal_width = width
    petal_length = (length - stem_length) / 2  # Adjust length for stem


    petal_horiz = c << rectangle(size=(length, width), layer=(1, 0), centered=True)
    petal_vert = c << rectangle(size=(width, length), layer=(1, 0), centered=True)


    # Create stems for each arm
    stem_size = (width, stem_length)
    stem_h_left = c << rectangle(size=stem_size, layer=(1, 0), centered=True)
    stem_h_right = c << rectangle(size=stem_size, layer=(1, 0), centered=True)
    stem_v_up = c << rectangle(size=stem_size, layer=(1, 0), centered=True)
    stem_v_down = c << rectangle(size=stem_size, layer=(1, 0), centered=True)


    # Position stems
    stem_h_left.move((-length / 2 - stem_length / 2 + width / 2 , 0))
    stem_h_right.move((length / 2 + stem_length / 2 - width / 2, 0))

    stem_v_up.move((0, length / 2 + stem_length / 2 - width / 2))
    stem_v_down.move((0, -length / 2 - stem_length / 2 + width / 2))

    return c

if __name__ == "__main__":
    c = my_flower_cross()
    c.show()  # Show in KLayout

    # Export to GDS
    c.write_gds("my_flower_cross.gds") # saves the component as a GDS file