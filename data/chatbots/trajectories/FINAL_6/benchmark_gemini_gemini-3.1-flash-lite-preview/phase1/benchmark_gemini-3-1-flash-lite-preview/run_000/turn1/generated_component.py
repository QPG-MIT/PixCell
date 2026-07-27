import gdsfactory as gf

@gf.cell
def stylized_cross():
    """
    Creates a 4-fold symmetric cross using parametric primitives 
    and boolean operations to merge the geometry.
    """
    c = gf.Component()
    layer = (1, 0)

    # 1. Define the base geometry (primitives)
    # Spindle petal
    petal = gf.components.ellipse(radii=(0.6, 1.8), layer=layer)
    # Rectangular tip
    tip = gf.components.rectangle(size=(0.6, 0.4), layer=layer, centered=True)

    # 2. Build one arm
    arm = gf.Component()
    arm << petal
    # Move tip to the end of the petal (1.8um radius + half of tip height)
    tip_ref = arm << tip
    tip_ref.move(destination=(0, 2.0))

    # 3. Create the 4-fold symmetric structure
    # We place 4 references of the 'arm' into a temporary component
    temp_comp = gf.Component()
    for angle in [0, 90, 180, 270]:
        ref = temp_comp << arm
        ref.rotate(angle)

    # 4. Perform boolean 'or'
    # This merges the overlapping references into a single unified polygon
    fused_geometry = gf.boolean(temp_comp, temp_comp, operation="or", layer=layer)
    
    # 5. Add the final fused geometry to our main component
    c << fused_geometry

    return c

# Generate and save the device
if __name__ == "__main__":
    device = stylized_cross()
    
    # This command explicitly saves the GDS file to your directory
    filename = "stylized_cross.gds"
    device.write_gds(filename)
    print(f"Successfully generated: {filename}")
    
    # Optional: Open in KLayout if available
    # device.show()