import gdsfactory as gf

@gf.cell
def petal():
    """Constructs a single petal primitive."""
    c = gf.Component()
    # Ellipse body
    c << gf.components.ellipse(radii=(0.6, 1.85), layer=(1, 0))
    # Rectangular tip positioned at the end of the ellipse
    # Center y = 1.85 (ellipse radius) + 0.25 (half of 0.5 rect height) = 2.1
    tip = c << gf.components.rectangle(size=(0.4, 0.5), layer=(1, 0), centered=True)
    tip.movey(2.1)
    return c

@gf.cell
def flower_device():
    """Assembles the 4 petals into a cross shape using boolean operations."""
    c = gf.Component()
    
    # 1. Generate four independent rotated components using gf.geometry.rotate
    # This avoids the "locked" error associated with in-place .rotate()
    p1 = petal()
    p2 = gf.geometry.rotate(petal(), angle=90)
    p3 = gf.geometry.rotate(petal(), angle=180)
    p4 = gf.geometry.rotate(petal(), angle=270)
    
    # 2. Perform boolean unions to merge the overlapping geometries
    # We chain the boolean operations together
    u1 = gf.boolean(p1, p2, operation="or", layer=(1, 0))
    u2 = gf.boolean(u1, p3, operation="or", layer=(1, 0))
    final_shape = gf.boolean(u2, p4, operation="or", layer=(1, 0))
    
    # 3. Add the final merged shape to the component
    c << final_shape
    return c

if __name__ == "__main__":
    device = flower_device()
    device.write_gds("flower_device.gds")
    print("GDS file 'flower_device.gds' successfully created.")