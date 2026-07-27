import gdsfactory as gf

@gf.cell
def get_petal_unit():
    """
    Creates a single unit consisting of one petal and one stem.
    We return a container component where we manipulate references.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Add Petal as a reference
    # Using 'c <<' creates a reference, not the definition
    petal_ref = c << gf.components.ellipse(radii=(1.5, 0.7), layer=layer)
    
    # 2. Add Stem as a reference
    stem_ref = c << gf.components.rectangle(size=(0.7, 0.3), layer=layer)
    
    # 3. Position the references using their relative coordinates
    # We move the stem to the tip of the ellipse (x=1.5)
    # The rectangle is 0.3 high, so we offset y by -0.15 to center it
    stem_ref.move((1.5, -0.15))
    
    return c

@gf.cell
def flower_device():
    """
    Creates the final device by assembling 4 petal units
    and performing a boolean union to merge them into one polygon.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # Create a temporary component to assemble the 4 units
    temp_c = gf.Component()
    
    # Add 4 units rotated
    for angle in [0, 90, 180, 270]:
        # Add reference of the unit
        unit_ref = temp_c << get_petal_unit()
        unit_ref.rotate(angle)
    
    # Perform boolean union on all shapes to create a single, clean polygon
    # This merges the overlaps and removes internal lines
    final_shape = gf.geometry.union(temp_c, layer=layer)
    
    # Add the flattened final shape to the main component
    c << final_shape
    
    return c

# Generate, save, and show
device = flower_device()
device.write_gds("flower_device.gds")
device.show()