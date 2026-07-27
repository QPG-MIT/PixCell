import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.typings import LayerSpec

@gf.cell
def cross_with_endcaps(length: float = 3.7, width: float = 0.7, endcap_length: float = 1.0, endcap_width: float = 0.7, layer: LayerSpec = (1, 0)):
    """
    Creates a cross shape with endcaps using GDSFactory parametric functions.

    Args:
        length: Total length of the cross arms.
        width: Width of the main cross arms.
        endcap_length: Length of the endcap extensions.
        endcap_width: Width of the endcap extensions.
        layer: The layer to put the cross on.

    Returns:
        A GDSFactory component representing the cross with endcaps.
    """
    c = gf.Component()

    # Horizontal arm
    horizontal = c << rectangle(size=(length, width), layer=layer)
    horizontal.move((-length / 2, -width / 2))

    # Vertical arm
    vertical = c << rectangle(size=(width, length), layer=layer)
    vertical.move((-width / 2, -length / 2))

    # Endcaps
    endcap_x_pos = c << rectangle(size=(endcap_length, endcap_width), layer=layer)
    endcap_x_neg = c << rectangle(size=(endcap_length, endcap_width), layer=layer)
    endcap_y_pos = c << rectangle(size=(endcap_width, endcap_length), layer=layer)
    endcap_y_neg = c << rectangle(size=(endcap_width, endcap_length), layer=layer)
    endcap_x_pos.movex(length/2)
    endcap_x_pos.movey(-endcap_width/2+ width/2- endcap_width/2 )
    endcap_x_neg.movex(-length/2 - endcap_length)
    endcap_x_neg.movey(-endcap_width/2+ width/2- endcap_width/2)
    endcap_y_pos.movey(length/2 )
    endcap_y_pos.movex(width/2- endcap_width/2)
    endcap_y_neg.movey(-length/2- endcap_length)
    endcap_y_neg.movex(width/2- endcap_width/2)

    # Return the component
    return c

if __name__ == "__main__":
    cross = cross_with_endcaps()
    cross.show()
    print(f"Footprint = {cross.bbox}")  # Corrected line: Use cross.bbox instead of cross.bbox_sizes