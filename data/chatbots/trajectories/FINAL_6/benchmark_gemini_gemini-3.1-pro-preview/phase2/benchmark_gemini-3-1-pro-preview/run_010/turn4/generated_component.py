import gdsfactory as gf

@gf.cell
def stylized_cross() -> gf.Component:
    """
    Creates a stylized cross with four solid petals that merge 
    in the center and extend into thin straight arms.
    """
    c = gf.Component()
    target_layer = (1, 0)

    # 1. Base Thin Cross
    # Provides the exact 4.7um footprint constraint and the outer thin arms.
    # Slightly thinner than before to emphasize the bulk of the petals.
    cross_len = 4.7
    cross_width = 0.12
    base_cross = gf.components.cross(length=cross_len, width=cross_width, layer=target_layer)
    
    # 2. Crossed Ellipses for the Petals
    # Instead of 4 displaced ellipses, we use 2 centered crossed ellipses.
    # This automatically creates a solid, un-pinched core where they overlap.
    rx = 1.8   # Half-length of the petal bulge
    ry = 0.55  # Half-width of the petal bulge (plumper than previous iteration)
    
    h_ellipse = gf.components.ellipse(radii=(rx, ry), layer=target_layer)
    v_ellipse = gf.components.ellipse(radii=(ry, rx), layer=target_layer)
    
    # 3. Boolean Composition
    # Merge the two ellipses to create the central blooming shape
    petals = gf.boolean(h_ellipse, v_ellipse, operation="or", layer=target_layer)
    
    # Merge the petals with the underlying backbone cross
    final_geom = gf.boolean(base_cross, petals, operation="or", layer=target_layer)
    
    # Add the unified geometry to our cell
    c << final_geom
    
    return c

if __name__ == "__main__":
    # Create the component
    c = stylized_cross()
    
    # Save the component to a GDS file
    c.write_gds("stylized_cross.gds")