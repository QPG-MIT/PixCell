import gdsfactory as gf

@gf.cell
def flower_device():
    """
    Creates a four-leaf flower geometry by creating a single arm and 
    boolean-unioning four rotated copies to form a contiguous shape.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # We construct the arm to ensure it tapers appropriately and 
    # connects to form a central square upon union.
    def create_arm():
        arm = gf.Component()
        
        # 1. Create Petal: Using an ellipse with radii (0.4, 0.6)
        # This gives a base width of 0.8 at the center (y=0), ensuring
        # that four arms will overlap to form a solid 0.8x0.8 central square.
        petal = arm << gf.components.ellipse(radii=(0.4, 0.6), layer=layer)
        # Move the center of the ellipse to (0, 0.6), so it spans y=0 to y=1.2
        petal.move((0, 0.6))
        
        # 2. Create Tip: A narrower rectangular extension
        # Size (0.25, 0.3). Placed at the end of the petal (y=1.2).
        # Centering it at y=1.35 puts the base of the tip at y=1.2.
        tip = arm << gf.components.rectangle(size=(0.25, 0.3), layer=layer, centered=True)
        tip.move((0, 1.35))
        
        return arm

    # Initialize the final shape with the first arm
    final_shape = create_arm()
    
    # Add 3 more arms rotated by 90, 180, and 270 degrees
    for angle in [90, 180, 270]:
        arm = create_arm()
        arm.rotate(angle)
        
        # Boolean OR merges the new arm with the existing structure,
        # creating the contiguous center and smooth petal transitions.
        final_shape = gf.boolean(final_shape, arm, operation="or", layer=layer)
    
    # Add the final merged shape to the main component
    c << final_shape
    
    return c

# Generate and save the device
if __name__ == "__main__":
    device = flower_device()
    device.write_gds("flower_device.gds")
    device.show()