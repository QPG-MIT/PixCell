import gdsfactory as gf

@gf.cell
def generate_recreated_device():
    """
    Recreates the device using parametric ellipses and a cross.
    The total footprint is constrained to 4.7um x 4.7um.
    """
    c = gf.Component("recreated_device")
    layer = (1, 0)
    
    # 1. Define dimensions based on the 4.7um footprint
    # The cross defines the total extent and the flat rectangular tips.
    total_length = 4.7
    tip_width = 0.45 
    
    # The ellipses create the bulging "petals". 
    # We make them slightly shorter (4.0um) than the cross so the 
    # rectangular tips remain distinct at the ends of the arms.
    petal_extent = 2.0 # Radius (Total length = 4.0um)
    petal_thickness = 0.65 # Radius (Total width = 1.3um)
    
    # 2. Create the parametric primitives
    # A cross for the rigid rectangular ends
    cross_tips = gf.components.cross(length=total_length, width=tip_width, layer=layer)
    
    # Two perpendicular ellipses for the curved petal arms
    ellipse_h = gf.components.ellipse(radii=(petal_extent, petal_thickness), layer=layer)
    ellipse_v = gf.components.ellipse(radii=(petal_thickness, petal_extent), layer=layer)
    
    # 3. Merge primitives using Boolean OR operations
    # First, combine the ellipses to form the smooth junction
    petals = gf.boolean(A=ellipse_h, B=ellipse_v, operation="or", layer=layer)
    
    # Finally, merge the petals with the cross to add the rectangular tips
    final_geometry = gf.boolean(A=petals, B=cross_tips, operation="or", layer=layer)
    
    # Add the resulting geometry to the main component
    c << final_geometry
    
    return c

if __name__ == "__main__":
    # Create the component
    device = generate_recreated_device()
    
    # EXPLICITLY WRITE THE GDS FILE
    # This ensures a file is produced for verification.
    device.write_gds("device.gds")