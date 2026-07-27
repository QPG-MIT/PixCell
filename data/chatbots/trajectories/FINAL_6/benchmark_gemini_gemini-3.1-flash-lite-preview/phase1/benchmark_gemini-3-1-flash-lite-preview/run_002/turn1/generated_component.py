import gdsfactory as gf

@gf.cell
def petal():
    """Creates one arm of the clover using component references."""
    c = gf.Component()
    
    # 1. Create references inside the component 'c'
    # By creating references (e) and (r), we can manipulate them
    # locally without violating the cache of the underlying shapes.
    e = c << gf.components.ellipse(radii=(1.6, 0.7), layer=(1, 0))
    r = c << gf.components.rectangle(size=(0.4, 0.4), layer=(1, 0))
    
    # 2. Position the rectangle relative to the ellipse
    # The ellipse is centered at (0,0). We move the rectangle to the edge.
    # r.movex(1.6) places the start of the rectangle at the ellipse boundary.
    # r.movey(-0.2) centers it vertically.
    r.movex(1.6)
    r.movey(-0.2)
    
    return c

@gf.cell
def clover_shape():
    """Constructs the full clover by rotating the petal component 4 times."""
    c = gf.Component()
    
    # Instantiate the petal component
    p = petal()
    
    # Create 4 instances
    for i in range(4):
        # Add the petal as a reference to the main component
        ref = c << p
        # Rotate each instance
        ref.rotate(i * 90)
        
    return c

if __name__ == "__main__":
    # Generate the clover
    device = clover_shape()
    
    # Save the file
    device.write_gds("clover.gds")
    print("GDS file 'clover.gds' produced successfully.")
    
    # Visualization (optional)
    device.show()