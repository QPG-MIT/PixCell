import gdsfactory as gf

@gf.cell
def elliptical_crossing() -> gf.Component:
    """
    Creates a crossing structure using a central thin cross and 
    overlapping ellipses to form the adiabatic petal-like transitions.
    """
    c = gf.Component()
    
    # Target footprint constraint: 4.7 um x 4.7 um
    total_length = 4.7
    
    # Proportions estimated from the visual geometry
    straight_width = 0.15  # Width of the thin rectangular arms at the tips
    ellipse_a = 1.9        # Major radius of the ellipses (3.8 um total length)
    ellipse_b = 0.65       # Minor radius of the ellipses (1.3 um max width)
    layer = (1, 0)
    
    # 1. Create the fundamental primitives
    # The cross component gives us the 4 straight arms and strictly enforces the 4.7um footprint
    base_cross = gf.components.cross(
        length=total_length, 
        width=straight_width, 
        layer=layer
    )
    
    # The ellipses create the smooth, bulky "petal" shapes for the crossing
    ellipse_horiz = gf.components.ellipse(
        radii=(ellipse_a, ellipse_b), 
        layer=layer
    )
    ellipse_vert = gf.components.ellipse(
        radii=(ellipse_b, ellipse_a), 
        layer=layer
    )
    
    # 2. Combine the geometry using Boolean OR operations
    # Merge the cross with the horizontal ellipse
    union_1 = gf.boolean(
        A=base_cross, 
        B=ellipse_horiz, 
        operation="or", 
        layer=layer
    )
    
    # Merge the result with the vertical ellipse to complete the shape
    final_shape = gf.boolean(
        A=union_1, 
        B=ellipse_vert, 
        operation="or", 
        layer=layer
    )
    
    # Add the unified geometry to our parent component
    c << final_shape
    
    return c

if __name__ == "__main__":
    # Generate the device
    device = elliptical_crossing()
    
    # Explicitly write to a GDS file so the output is properly recorded
    device.write_gds("elliptical_crossing.gds")