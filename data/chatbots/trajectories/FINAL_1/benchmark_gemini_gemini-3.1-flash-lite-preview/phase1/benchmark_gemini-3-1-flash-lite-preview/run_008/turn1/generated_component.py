import gdsfactory as gf

@gf.cell
def tapered_splitter():
    """
    Recreates the tapered Y-splitter geometry.
    Uses c.flatten() to ensure all coordinates are grid-snapped.
    """
    c = gf.Component()
    
    # 1. Define dimensions
    length = 40.0
    width_in = 0.85
    width_out = 0.4
    
    # 2. Create the taper primitives
    taper_primitive = gf.components.taper(length=length, width1=width_in, width2=width_out)
    
    # 3. Create references
    top_arm = c << taper_primitive
    bot_arm = c << taper_primitive
    
    # 4. Position and rotate
    # Move vertically to create the split gap
    top_arm.movey(width_in / 2)
    bot_arm.movey(-width_in / 2)
    
    # Rotate to create divergence
    # We rotate around the origin (the input side)
    top_arm.rotate(angle=2, center=(0, 0))
    bot_arm.rotate(angle=-2, center=(0, 0))
    
    # 5. Boolean Operation
    # We create a new component from the boolean operation
    # This effectively merges the two shapes into one set of polygons
    splitter_shape = gf.boolean(top_arm, bot_arm, operation="or", layer=(1, 0))
    
    # Add the merged geometry to our final component
    c.add_ref(splitter_shape)
    
    # 6. Flatten to resolve off-grid instance errors
    # This converts rotated references into fixed grid-snapped polygons
    c.flatten()
    
    return c

# Generate and save
device = tapered_splitter()
device.write_gds("tapered_splitter.gds")

# Preview
device.show()