import gdsfactory as gf

@gf.cell
def cross_with_petals():
    """Creates a cross with rounded petals."""
    c = gf.Component()

    petal_length = 2
    petal_width = 1
    petal_stem = 0.5

    # Create petal shape using a rounded rectangle (stems) and circles
    petal = gf.Component()

    # Add stems to the component
    rect = petal << gf.components.rectangle(size=(petal_stem, petal_width), layer=(1, 0), centered=True)
    # petal.add_port("o1", port=rect.ports["o1"]) #No named port exists here. Can be removed
    # petal.add_port("o2", port=rect.ports["o2"]) #No named port exists here. Can be removed

    # Create a petal body out of a circle on top of the stem
    circle = petal << gf.components.circle(radius=petal_length/2, layer=(1, 0))
    circle.movey(petal_length / 2 + petal_stem/2) # Translate the circle so the top of the circle is centered on the stem
    
    # petal.add_port("o3", port=circle.ports["o1"]) #No named port exists here. Can be removed
    # petal.add_port("o4", port=circle.ports["o2"]) #No named port exists here. Can be removed
    
    petal = gf.boolean(petal, rect, operation="or", layer=(1, 0))
    petal = gf.boolean(petal, circle, operation="or", layer=(1, 0))

    # Place four petals around the center
    p1 = c << petal
    p2 = c << petal
    p3 = c << petal
    p4 = c << petal
    
    p2.rotate(90)
    p2.movex(-petal_stem/2 - petal_length/2)
    p3.rotate(180)
    p4.rotate(270)
    p4.movex(petal_stem/2 + petal_length/2)
    

    return c

if __name__ == "__main__":
    c = cross_with_petals()
    c.show()