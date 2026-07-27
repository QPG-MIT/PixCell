import gdsfactory as gf

@gf.cell
def petal():
    """Creates a petal with the geometry already positioned correctly."""
    c = gf.Component()
    
    # We add references using 'origin' and 'rotation' arguments directly.
    # This prevents the "Locked" error because we don't modify the reference after creation.
    
    # 1. Ellipse at center (0,0)
    c.add_ref(gf.components.ellipse(radii=(1.5, 0.7), layer=(1, 0)), origin=(0, 0))
    
    # 2. Rectangle placed at the tip (1.25, -0.25)
    c.add_ref(gf.components.rectangle(size=(0.5, 0.5), layer=(1, 0)), origin=(1.25, -0.25))
    
    return c

@gf.cell
def clover():
    """Constructs the clover by adding petals at rotated positions."""
    c = gf.Component()
    
    # Add 4 petal instances, applying rotation at the moment of addition
    for i in range(4):
        c.add_ref(petal(), rotation=i * 90)
    
    # To create a single fused polygon (the 'clover' shape), 
    # we use boolean operations to merge the overlapping parts.
    # We take the component and perform an OR operation on itself.
    fused_clover = gf.boolean(c, c, operation="or", layer=(1, 0))
    
    return fused_clover

if __name__ == "__main__":
    # Generate the clover
    device = clover()
    
    # Save the file
    device.write_gds("clover.gds")
    print("GDS file 'clover.gds' produced successfully as a single fused shape.")
    
    # Visualization
    device.show()