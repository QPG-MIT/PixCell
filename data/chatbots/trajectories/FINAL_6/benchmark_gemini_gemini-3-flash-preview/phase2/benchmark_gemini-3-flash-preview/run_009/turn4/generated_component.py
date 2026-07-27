import gdsfactory as gf

@gf.cell
def recreate_cross_petal_v4():
    """
    Iteration 4: Optimized petal geometry to match target "waist" and curvature.
    
    Key improvements:
    - Increased petal offset to sharpen the central intersection.
    - Adjusted ellipse aspect ratio for a more tapered, "seed" look.
    - Fixed the 4.7um footprint via the base cross component.
    """
    c = gf.Component("cross_petal_v4")
    layer = (1, 0)
    
    # 1. Dimensions based on 4.7um footprint constraint
    total_size = 4.7
    half_size = total_size / 2 # 2.35um
    
    # 2. Geometric Parameters
    # width of the terminal rectangular tips
    tip_width = 0.28 
    # semi-major axis: length of the petal bulge
    petal_rx = 1.12  
    # semi-minor axis: half-width of the petal bulge
    petal_ry = 0.68  
    # distance from origin to center of ellipse
    # Increasing this makes the center "waist" thinner
    petal_offset = 1.08 
    
    # 3. Create the base cross
    # This defines the absolute 4.7um extent and the rectangular tips
    main_cross = gf.components.cross(
        length=total_size, 
        width=tip_width, 
        layer=layer
    )
    
    # 4. Create Petal Templates
    petal_h = gf.components.ellipse(radii=(petal_rx, petal_ry), layer=layer)
    petal_v = gf.components.ellipse(radii=(petal_ry, petal_rx), layer=layer)
    
    # 5. Position Petals
    # We position them so they overlap slightly at the center (vertex at ~ -0.04um)
    p_right = petal_h.copy().move((petal_offset, 0))
    p_left = petal_h.copy().move((-petal_offset, 0))
    p_top = petal_v.copy().move((0, petal_offset))
    p_bottom = petal_v.copy().move((0, -petal_offset))
    
    # 6. Boolean Assembly
    # Merge the cross and the four petals into one clean polygon
    final_shape = main_cross
    for petal in [p_right, p_left, p_top, p_bottom]:
        final_shape = gf.boolean(
            A=final_shape, 
            B=petal, 
            operation="or", 
            layer=layer
        )
    
    c.add_ref(final_shape)
    
    # Validation
    # print(f"Device Footprint: {c.xsize:.3f} x {c.ysize:.3f} um")
    return c

if __name__ == "__main__":
    device = recreate_cross_petal_v4()
    device.write_gds("cross_petal_v4.gds")
    # device.show()