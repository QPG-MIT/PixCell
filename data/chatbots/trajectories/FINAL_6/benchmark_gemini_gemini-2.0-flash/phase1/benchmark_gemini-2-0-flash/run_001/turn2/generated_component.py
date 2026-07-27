import gdsfactory as gf
from gdsfactory.components import rectangle

@gf.cell
def my_simple_cross(length=5.0, width=1.0):
    """
    Recreates a simple cross geometry using GDSFactory primitives.
    """
    c = gf.Component("my_simple_cross")

    # Create horizontal rectangle
    horizontal_rect = c << rectangle(size=(length, width), layer=(1, 0), centered=True)

    # Create vertical rectangle
    vertical_rect = c << rectangle(size=(width, length), layer=(1, 0), centered=True)

    return c

if __name__ == "__main__":
    c = my_simple_cross()
    c.show()  # Show in KLayout
    c.write_gds("my_simple_cross.gds")  # Save as GDS file