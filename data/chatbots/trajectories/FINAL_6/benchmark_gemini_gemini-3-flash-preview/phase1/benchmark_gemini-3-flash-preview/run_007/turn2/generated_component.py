import gdsfactory as gf

@gf.cell
def generate_recreated_device():
    """
    Recreates the device using a central cross and four offset ellipses.
    Moves the ellipses away from the center to create a 'pinched' junction,
    then merges them with a cross to define the rectangular tips.
    """
    # Main container component
    c = gf.Component("recreated_device")
    layer = (1, 0)
    
    # 1. Dimensions based on the 4.7um x 4.7um footprint
    total_length = 4.7
    tip_width = 0.4  # Matches the width of the rectangular extremities
    
    # 2. Petal Geometry Parameters
    # By shifting the ellipses, the central overlap is minimized,
    # creating the curved 'waist' between the arms.
    rx = 1.25  # Ellipse radius along the arm
    ry = 0.7   # Ellipse radius across the arm (thickness)
    offset = 1.1  # Distance from the origin to the center of each ellipse
    
    # Create the base primitives (these are the locked/cached cells)
    ellipse_base = gf.components.ellipse(radii=(rx, ry), layer=layer)
    cross_base = gf.components.cross(length=total_length, width=tip_width, layer=layer)
    
    # 3. Assemble the 'Petal Group'
    # We add references to the base ellipse and move the REFERENCES.
    petals = gf.Component("petal_group")
    
    # Right Petal
    ref_r = petals << ellipse_base
    ref_r.movex(offset)
    
    # Left Petal
    ref_l = petals << ellipse_base
    ref_l.movex(-offset)
    
    # Top Petal
    ref_t = petals << ellipse_base
    ref_t.rotate(90)
    ref_t.movey(offset)
    
    # Bottom Petal
    ref_b = petals << ellipse_base
    ref_b.rotate(90)
    ref_b.movey(-offset)
    
    # 4. Perform Boolean Operations
    # Boolean OR combines the petals and the cross into a single shape.
    # gf.boolean flattens the input components and returns a new one.
    final_geom = gf.boolean(A=petals, B=cross_base, operation="or", layer=layer)
    
    # Add the result of the boolean operation to our final component
    c << final_geom
    
    return c

if __name__ == "__main__":
    # Generate the component
    device = generate_recreated_device()
    
    # Write the GDS file for verification (Crucial for output)
    device.write_gds("device.gds")