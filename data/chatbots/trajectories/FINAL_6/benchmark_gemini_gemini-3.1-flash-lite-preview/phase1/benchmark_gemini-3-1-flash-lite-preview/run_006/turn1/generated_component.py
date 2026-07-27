import gdsfactory as gf

@gf.cell
def flower_device():
    """
    Recreates the flower geometry using parametric primitives 
    and boolean unions.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Define Primitive Shapes
    # Ellipse radii chosen to fit within the 4.7um footprint
    petal = gf.components.ellipse(radii=(1.5, 0.6), layer=layer)
    # Rectangle chosen to look like the extension legs
    leg = gf.components.rectangle(size=(0.8, 0.2), layer=layer, centered=True)
    
    # 2. Construct the Flower Body (4 rotated petals)
    # We use boolean 'or' to merge them into a single, seamless object
    flower_body = petal
    for angle in [90, 180, 270]:
        rotated_petal = petal.copy().rotate(angle)
        flower_body = gf.boolean(flower_body, rotated_petal, operation="or", layer=layer)
        
    # 3. Construct and Attach the Legs
    # We define the positions for the 4 legs (x, y, rotation)
    # The petal extends to 1.5um, so we place legs at 1.9um to extend outwards
    legs_config = [
        (1.9, 0, 0),    # Right
        (0, 1.9, 90),   # Top
        (-1.9, 0, 0),   # Left
        (0, -1.9, 90)   # Bottom
    ]
    
    final_device = flower_body
    for x, y, angle in legs_config:
        # Create a copy, rotate, and move to the tip of the petal
        current_leg = leg.copy().rotate(angle).move((x, y))
        # Union the leg with the body
        final_device = gf.boolean(final_device, current_leg, operation="or", layer=layer)
    
    # 4. Add the final structure to the component
    c << final_device
    return c

# Generate the component
device = flower_device()

# Save and visualize
device.write_gds("flower_device.gds")
device.show()