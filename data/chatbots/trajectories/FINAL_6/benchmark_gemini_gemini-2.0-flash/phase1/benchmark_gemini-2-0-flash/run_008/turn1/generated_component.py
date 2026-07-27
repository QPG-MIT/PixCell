import gdsfactory as gf
from gdsfactory.components import rectangle

@gf.cell
def four_leaf_clover(length=4.7, width=1.175, layer=(1, 0)):
    """
    A four-leaf clover shape.

    Args:
        length: Total length of the clover.
        width: Width of each lobe.
        layer: GDS layer.
    """
    c = gf.Component()

    # Calculate internal dimensions
    lobe_length = (length - width) / 2
    lobe_width = width # For the sake of naming conventions

    # Create the lobes
    lobe_top = c << rectangle(size=(lobe_length, lobe_width), layer=layer, centered=True)
    lobe_bottom = c << rectangle(size=(lobe_length, lobe_width), layer=layer, centered=True)
    lobe_left = c << rectangle(size=(lobe_width, lobe_length), layer=layer, centered=True)
    lobe_right = c << rectangle(size=(lobe_width, lobe_length), layer=layer, centered=True)

    # Place the lobes (relative to center, but center defined after)
    lobe_top.movey(length / 2 - lobe_width/2)
    lobe_bottom.movey(-length / 2 + lobe_width/2)
    lobe_left.movex(-length / 2 + lobe_width/2)
    lobe_right.movex(length / 2 - lobe_width/2)
    
    #Boolean
    result = c << gf.boolean(lobe_top, lobe_bottom, operation="or", layer=layer)
    result2 = c << gf.boolean(result, lobe_left, operation="or", layer=layer)
    final_component = gf.boolean(result2, lobe_right, operation="or", layer=layer)
    c.add(final_component) # add the result into the component
    return c

if __name__ == "__main__":
    c = four_leaf_clover()
    c.show()
    c.write_gds("four_leaf_clover.gds") # saves the GDS file