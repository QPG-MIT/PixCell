import gdsfactory as gf

@gf.cell
def custom_clover():
    """
    Creates a 4-petaled clover shape with rectangular tips,
    constructed using primitives and boolean operations.
    """
    c = gf.Component()
    
    # Define parameters based on 4.7um footprint constraint
    # Petal radius 2.1um + Tip protrusion 0.25um = 2.35um radius
    # 2.35um * 2 = 4.7um total width
    petal_radii = (2.1, 0.7)
    tip_size = (0.5, 0.3)
    
    # Base primitives
    petal_base = gf.components.ellipse(radii=petal_radii, layer=(1, 0))
    tip_base = gf.components.rectangle(size=tip_size, centered=True, layer=(1, 0))
    
    # List to hold all parts for boolean union
    parts = []
    
    # Assemble the 4 symmetric arms
    for angle in [0, 90, 180, 270]:
        # 1. Add Petal
        petal = c << petal_base
        petal.rotate(angle)
        parts.append(petal)
        
        # 2. Add Tip
        # Move to edge of petal (2.1um) and rotate
        tip = c << tip_base
        tip.movex(2.1)
        tip.rotate(angle)
        parts.append(tip)
        
    # Perform Boolean Union to create a single geometry
    # We start with the first part and union it with the others
    union = parts[0]
    for i in range(1, len(parts)):
        union = gf.boolean(union, parts[i], operation="or", layer=(1, 0))
        
    return union

# Generate and visualize
if __name__ == "__main__":
    device = custom_clover()
    # Write to GDS
    device.write_gds("clover_shape.gds")
    # Show it
    device.show()