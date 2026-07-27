import gdsfactory as gf

@gf.cell
def recreate_refined_cross_petal():
    """
    Refined version of the cross-petal device.
    Adjusted proportions for a thinner, more elongated look to match the source.
    Constraint: 4.7um x 4.7um footprint.
    """
    c = gf.Component("refined_device")
    layer = (1, 0)
    
    # 1. Constants based on visual analysis of the target image
    total_size = 4.7
    tip_width = 0.32       # Thinner stems
    petal_max_width = 1.0  # Narrower bulges
    petal_span = 3.6       # Length of the curved part
    
    # 2. Create the cross for the rectangular tips
    # This defines the absolute 4.7um boundary
    main_cross = gf.components.cross(
        length=total_size, 
        width=tip_width, 
        layer=layer
    )
    
    # 3. Create elongated ellipses for the petals
    # major_radius = petal_span / 2
    # minor_radius = petal_max_width / 2
    major_r = petal_span / 2  # 1.8um
    minor_r = petal_max_width / 2  # 0.5um
    
    ellipse_h = gf.components.ellipse(radii=(major_r, minor_r), layer=layer)
    ellipse_v = gf.components.ellipse(radii=(minor_r, major_r), layer=layer)
    
    # 4. Combine using Boolean OR
    # Merging the two ellipses and the cross creates the smooth transition 
    # from the bulging center to the flat rectangular tips.
    petals = gf.boolean(A=ellipse_h, B=ellipse_v, operation="or", layer=layer)
    final_shape = gf.boolean(A=petals, B=main_cross, operation="or", layer=layer)
    
    c.add_ref(final_shape)
    return c

if __name__ == "__main__":
    device = recreate_refined_cross_petal()
    
    # Generate GDS file
    device.write_gds("refined_device.gds")
    
    print("Refined GDS file 'refined_device.gds' produced.")
    print(f"Footprint Check: {device.xsize:.2f} x {device.ysize:.2f} um")