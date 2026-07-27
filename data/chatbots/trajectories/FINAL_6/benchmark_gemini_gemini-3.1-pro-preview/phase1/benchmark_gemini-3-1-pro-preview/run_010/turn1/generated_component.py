import gdsfactory as gf

@gf.cell
def stylized_cross() -> gf.Component:
    """
    Creates a stylized cross geometry with curved 'petal' arms 
    that terminate into thin straight segments.
    """
    c = gf.Component()
    
    # Define standard layer to use for all shapes
    target_layer = (1, 0)

    # 1. Base Thin Cross
    # Sets the exact overall footprint to [4.7, 4.7] constraint 
    # and provides the thin straight segments at the extremities.
    base_cross = gf.components.cross(length=4.7, width=0.2, layer=target_layer)
    
    # 2. Horizontal & Vertical Petals
    # We use ellipses to create the thick, smoothly curved body of the arms.
    # Radii are tuned to match the visual proportions of the original image 
    # (leaving ~0.55um of thin straight line exposed at each tip).
    petal_h = gf.components.ellipse(radii=(1.8, 0.8), layer=target_layer)
    petal_v = gf.components.ellipse(radii=(0.8, 1.8), layer=target_layer)
    
    # 3. Boolean Composition
    # Merge the shapes to form a clean, continuous single-polygon structure.
    # The 'layer' argument is required for the output of a boolean operation.
    merge_step_1 = gf.boolean(base_cross, petal_h, operation="or", layer=target_layer)
    final_geometry = gf.boolean(merge_step_1, petal_v, operation="or", layer=target_layer)
    
    # Add the unified geometry to our cell
    c << final_geometry
    
    return c

if __name__ == "__main__":
    # Create the component
    c = stylized_cross()
    
    # Save the component to a GDS file (required for output verification)
    c.write_gds("stylized_cross.gds")