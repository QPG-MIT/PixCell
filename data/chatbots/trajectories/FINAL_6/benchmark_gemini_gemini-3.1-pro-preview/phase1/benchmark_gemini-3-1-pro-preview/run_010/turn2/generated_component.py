import gdsfactory as gf

@gf.cell
def stylized_cross() -> gf.Component:
    """
    Creates a stylized cross with four separated petal structures that 
    bloom from the center and taper into thin straight arms.
    """
    c = gf.Component()
    target_layer = (1, 0)

    # 1. Base Thin Cross
    # Provides the exact 4.7um footprint constraint and the central "backbone"
    base_cross = gf.components.cross(length=4.7, width=0.15, layer=target_layer)
    
    # 2. Create the 4 Petals
    # Instead of two giant overlapping ellipses, we use four smaller ellipses
    # shifted outwards so they meet cleanly at the origin.
    petals = gf.Component()
    rx = 0.95  # Half-length of a petal
    ry = 0.45  # Half-width of a petal
    
    # Right petal (shifted right)
    ref_r = petals << gf.components.ellipse(radii=(rx, ry), layer=target_layer)
    ref_r.movex(rx)
    
    # Left petal (shifted left)
    ref_l = petals << gf.components.ellipse(radii=(rx, ry), layer=target_layer)
    ref_l.movex(-rx)
    
    # Top petal (shifted up, swap radii for vertical orientation)
    ref_t = petals << gf.components.ellipse(radii=(ry, rx), layer=target_layer)
    ref_t.movey(rx)
    
    # Bottom petal (shifted down)
    ref_b = petals << gf.components.ellipse(radii=(ry, rx), layer=target_layer)
    ref_b.movey(-rx)
    
    # 3. Boolean Composition
    # Merge the backbone cross and the 4 petals into a single continuous polygon.
    final_geom = gf.boolean(base_cross, petals, operation="or", layer=target_layer)
    
    # Add the unified geometry to our cell
    c << final_geom
    
    return c

if __name__ == "__main__":
    # Create the component
    c = stylized_cross()
    
    # Save the component to a GDS file
    c.write_gds("stylized_cross.gds")