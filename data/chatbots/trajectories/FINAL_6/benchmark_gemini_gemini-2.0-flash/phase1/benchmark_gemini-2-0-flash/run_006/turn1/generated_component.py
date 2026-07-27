import gdsfactory as gf

@gf.cell
def flower_cross(length: float = 4.7, width: float = 0.7, petal_length: float = 1.5) -> gf.Component:
    """
    Creates a cross-like shape with rounded petals at the ends of each arm.

    Args:
        length: Total length of the cross.
        width: Width of the straight section of the cross.
        petal_length: Length of each petal.
    """
    c = gf.Component()

    # 1. Create a simple cross
    cross = c << gf.components.cross(length=length, width=width, layer=(1, 0))

    # 2. Create the petals as circles.  We will offset them.
    petal_radius = petal_length / 2
    petal_component = gf.components.circle(radius=petal_radius, layer=(1, 0))



    # 3. Place and connect the petals
    # Calculate the distance from the cross center to place the petals
    petal_offset = (length / 2) + petal_radius
    petal = c << petal_component
    petal.move((petal_offset,0)) #Move it to right
    petal_top = c << petal_component
    petal_top.rotate(90)
    petal_top.move((0,petal_offset)) #move it to top

    petal_left = c << petal_component
    petal_left.rotate(180)
    petal_left.move((-petal_offset,0))

    petal_bottom = c << petal_component
    petal_bottom.rotate(270)
    petal_bottom.move((0,-petal_offset))

    # 4. Boolean operation to unite the shapes
    final_shape = gf.boolean(cross, petal, operation="or", layer=(1, 0))
    final_shape = gf.boolean(final_shape, petal_top, operation="or", layer=(1, 0))
    final_shape = gf.boolean(final_shape, petal_left, operation="or", layer=(1, 0))
    final_shape = gf.boolean(final_shape, petal_bottom, operation="or", layer=(1, 0))

    c.add(final_shape)

    return c

if __name__ == "__main__":
    cross = flower_cross()
    cross.show(show_ports=True)