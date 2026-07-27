import gdsfactory as gf

@gf.cell
def petal():
    """Creates a single petal unit: Ellipse lobe + Rectangle tip."""
    c = gf.Component()
    
    # 1. Ellipse (the lobe)
    # Radius of 1.8um (x) and 0.8um (y)
    lobe = c << gf.components.ellipse(radii=(1.8, 0.8), layer=(1, 0))
    
    # 2. Rectangular tip
    # Size 0.4um length, 0.3um width.
    tip = c << gf.components.rectangle(size=(0.4, 0.3), layer=(1, 0), centered=True)
    
    # Position rectangle at the tip of the ellipse (1.8um from center)
    # 1.8 (ellipse radius) + 0.2 (half of tip length 0.4) = 2.0um center position
    tip.movex(2.0)
    
    return c

@gf.cell
def device():
    """Assembles 4 petals and performs boolean union to create the final shape."""
    # Create 4 component instances of the petal
    p0 = petal()
    p1 = petal()
    p2 = petal()
    p3 = petal()
    
    # Rotate them (components can be rotated in-place before boolean operation)
    p1.rotate(90)
    p2.rotate(180)
    p3.rotate(270)
    
    # Boolean union: Chain operations to merge the 4 petals into 1 component
    # We use the catalog-specified gf.boolean(A, B, operation="or")
    
    # Merge p0 and p1
    union1 = gf.boolean(p0, p1, operation="or", layer=(1, 0))
    # Merge result with p2
    union2 = gf.boolean(union1, p2, operation="or", layer=(1, 0))
    # Merge result with p3
    final_device = gf.boolean(union2, p3, operation="or", layer=(1, 0))
    
    return final_device

if __name__ == "__main__":
    # Generate and save the device
    c = device()
    c.write_gds("flower_device.gds")
    print("GDS file generated: flower_device.gds")