import gdsfactory as gf

@gf.cell
def stylized_cross() -> gf.Component:
    """
    Creates a stylized cross with four blooming petals that pinch 
    at the center and taper into thin straight arms.
    """
    c = gf.Component()
    target_layer = (1, 0)

    # 1. Base Thin Cross
    # Provides the exact 4.7um footprint constraint and the outer thin arms
    cross_len = 4.7
    cross_width = 0.15
    base_cross = gf.components.cross(length=cross_len, width=cross_width, layer=target_layer)
    
    # 2. Create the 4 Petals
    # By making the center offset (cx) slightly LESS than the radius (rx),
    # the ellipses overlap at the origin. This avoids the infinite-slope 
    # bluntness of an ellipse tip and creates sharp, pinched inner corners.
    petals = gf.Component()
    rx = 1.0   # Half-length of the ellipse
    ry = 0.4   # Half-width of the ellipse
    cx = 0.9   # Center position of the ellipse (cx < rx forces overlap at origin)
    
    # Right petal 
    ref_r = petals << gf.components.ellipse(radii=(rx, ry), layer=target_layer)
    ref_r.movex(cx)
    
    # Left petal 
    ref_l = petals << gf.components.ellipse(radii=(rx, ry), layer=target_layer)
    ref_l.movex(-cx)
    
    # Top petal (swap radii for vertical orientation)
    ref_t = petals << gf.components.ellipse(radii=(ry, rx), layer=target_layer)
    ref_t.movey(cx)
    
    # Bottom petal
    ref_b = petals << gf.components.ellipse(radii=(ry, rx), layer=target_layer)
    ref_b.movey(-cx)
    
    # 3. Boolean Composition
    # Merge the backbone cross and the overlapping petals.
    # The base_cross will gracefully emerge from the tips of the ellipses.
    final_geom = gf.boolean(base_cross, petals, operation="or", layer=target_layer)
    
    # Add the unified geometry to our cell
    c << final_geom
    
    return c

if __name__ == "__main__":
    # Create the component
    c = stylized_cross()
    
    # Save the component to a GDS file
    c.write_gds("stylized_cross.gds")