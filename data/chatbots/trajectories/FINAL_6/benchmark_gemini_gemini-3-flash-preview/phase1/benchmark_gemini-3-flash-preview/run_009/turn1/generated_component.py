import gdsfactory as gf

@gf.cell
def recreate_cross_petal_device():
    """
    Recreates the device geometry from the provided image.
    Uses a cross for the tips and two orthogonal ellipses for the petal body.
    Constraint: 4.7um x 4.7um footprint.
    """
    c = gf.Component("cross_petal_device")
    layer = (1, 0)
    
    # 1. Create the central cross to define the rectangular tips and total footprint
    # length = 4.7um ensures it fits the footprint exactly.
    main_cross = gf.components.cross(
        length=4.7, 
        width=0.4, 
        layer=layer
    )
    
    # 2. Create the "petal" body using two perpendicular ellipses.
    # We set radii so that the curved body is slightly smaller than the cross tips.
    # Major radius 2.15um -> 4.3um span (leaving 0.2um tips on each side).
    major_r = 2.15
    minor_r = 0.85
    
    ellipse_h = gf.components.ellipse(radii=(major_r, minor_r), layer=layer)
    ellipse_v = gf.components.ellipse(radii=(minor_r, major_r), layer=layer)
    
    # 3. Combine primitives using boolean OR operations
    # First merge the two ellipses
    petals = gf.boolean(
        A=ellipse_h, 
        B=ellipse_v, 
        operation="or", 
        layer=layer
    )
    
    # Then merge with the cross to add the rectangular terminations
    final_shape = gf.boolean(
        A=petals, 
        B=main_cross, 
        operation="or", 
        layer=layer
    )
    
    # Add the result to the component
    c << final_shape
    
    return c

if __name__ == "__main__":
    # Generate the component
    device = recreate_cross_petal_device()
    
    # Write the GDS file to the current directory
    # This ensures a physical file is produced
    device.write_gds("device.gds")
    
    print("GDS file 'device.gds' has been produced.")
    print(f"Dimensions: {device.xsize:.2f} x {device.ysize:.2f} um")