import gdsfactory as gf
from gdsfactory.component import Component

@gf.cell
def flower_cross() -> Component:
    """Creates a flower-like cross shape using parametric primitives."""
    c = gf.Component("flower_cross")

    # Define parameters based on the desired shape and footprint
    petal_length = 2.35
    petal_width = 1.5
    stem_width = 0.3
    stem_length = 0.7

    # Create petal shapes
    petal_top = c << gf.components.ellipse(radii=(petal_length, petal_width), layer=(1, 0))
    petal_bottom = c << gf.components.ellipse(radii=(petal_length, petal_width), layer=(1, 0))
    petal_left = c << gf.components.ellipse(radii=(petal_width, petal_length), layer=(1, 0))
    petal_right = c << gf.components.ellipse(radii=(petal_width, petal_length), layer=(1, 0))

    # Create stem shapes
    stem_top = c << gf.components.rectangle(size=(stem_width, stem_length), layer=(1, 0), centered=True)
    stem_bottom = c << gf.components.rectangle(size=(stem_width, stem_length), layer=(1, 0), centered=True)
    stem_left = c << gf.components.rectangle(size=(stem_length, stem_width), layer=(1, 0), centered=True)
    stem_right = c << gf.components.rectangle(size=(stem_length, stem_width), layer=(1, 0), centered=True)
    
    # Place the petals around the center
    petal_top.movey(petal_length + stem_length / 2)
    petal_bottom.movey(-petal_length - stem_length / 2)
    petal_left.movex(-petal_length - stem_length / 2)
    petal_right.movex(petal_length + stem_length / 2)

    # Place stems
    stem_top.movey(petal_length + stem_length)
    stem_bottom.movey(-petal_length - stem_length)
    stem_left.movex(-petal_length - stem_length)
    stem_right.movex(petal_length + stem_length)

    # Combine all shapes using a boolean operation
    c = gf.boolean(
        petal_top, 
        petal_bottom, 
        operation="or", layer=(1, 0)
    )
    c = gf.boolean(
        c, 
        petal_left, 
        operation="or", layer=(1, 0)
    )
    c = gf.boolean(
        c, 
        petal_right, 
        operation="or", layer=(1, 0)
    )
    c = gf.boolean(
        c, 
        stem_top, 
        operation="or", layer=(1, 0)
    )
    c = gf.boolean(
        c, 
        stem_bottom, 
        operation="or", layer=(1, 0)
    )
    c = gf.boolean(
        c, 
        stem_left, 
        operation="or", layer=(1, 0)
    )
    c = gf.boolean(
        c, 
        stem_right, 
        operation="or", layer=(1, 0)
    )

    return c


if __name__ == "__main__":
    flower = flower_cross()
    flower.show(show_ports=False)
    print(flower.size_info)
    # Output looks correct within expected footprint