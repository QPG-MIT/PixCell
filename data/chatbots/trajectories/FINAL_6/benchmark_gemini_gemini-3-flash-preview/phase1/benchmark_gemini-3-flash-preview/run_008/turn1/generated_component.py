import gdsfactory as gf

@gf.cell
def bulging_cross_device():
    """
    Recreates the 4-fold symmetric device from the image.
    Uses ellipses for the bulging petals and a cross for the rectangular tips.
    Footprint: 4.7um x 4.7um.
    """
    layer = (1, 0)
    total_span = 4.7      # Constrained by footprint
    tip_width = 0.3       # Width of the rectangular ends
    petal_max_width = 1.2 # The "bulge" thickness
    petal_length = 3.8    # The extent of the elliptical bulge
    
    # 1. Create the cardinal tips using a cross primitive
    # This ensures the total footprint is exactly 4.7 x 4.7
    tips = gf.components.cross(
        length=total_span, 
        width=tip_width, 
        layer=layer
    )
    
    # 2. Create the bulging petals using ellipses
    # radii=(x_radius, y_radius)
    ellipse_h = gf.components.ellipse(
        radii=(petal_length / 2, petal_max_width / 2), 
        layer=layer
    )
    ellipse_v = gf.components.ellipse(
        radii=(petal_max_width / 2, petal_length / 2), 
        layer=layer
    )
    
    # 3. Combine the primitives using Boolean OR operations
    # First merge the two ellipses
    petals = gf.boolean(
        A=ellipse_h, 
        B=ellipse_v, 
        operation="or", 
        layer=layer
    )
    
    # Merge the petals with the cross-tips
    device = gf.boolean(
        A=petals, 
        B=tips, 
        operation="or", 
        layer=layer
    )
    
    return device

if __name__ == "__main__":
    # Create the component
    c = bulging_cross_device()
    
    # CORRECTED: Use dxsize and dysize to verify the footprint
    # These are the standard attributes in newer GDSFactory/kfactory versions
    print(f"Device dimensions: {c.dxsize:.2f} um x {c.dysize:.2f} um")
    
    # Display and save
    c.show()
    c.write_gds("bulging_cross.gds")