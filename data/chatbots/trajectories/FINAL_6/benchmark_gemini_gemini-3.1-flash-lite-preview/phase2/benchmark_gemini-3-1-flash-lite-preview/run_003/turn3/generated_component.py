import gdsfactory as gf

@gf.cell
def flower_device():
    """
    Creates a four-leaf flower geometry by creating a single arm and 
    boolean-unioning four rotated copies to form a contiguous shape.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # Dimensions defined to fit within the 4.7um footprint
    # Ellipse (petal): Radii (0.5, 1.0) -> Height = 2.0um
    # Tip (rectangle): Size (0.4, 0.4)
    
    def create_arm():
        arm = gf.Component()
        
        # 1. Create Petal
        petal = arm << gf.components.ellipse(radii=(0.5, 1.0), layer=layer)
        # Move up so the base touches the origin (0,0)
        petal.move((0, 1.0))
        
        # 2. Create Tip
        tip = arm << gf.components.rectangle(size=(0.4, 0.4), layer=layer, centered=True)
        # Move to the end of the petal (at y = 2.0 + tip_half_height = 2.2)
        tip.move((0, 2.2))
        
        return arm

    # Generate the full flower using boolean union
    # We initialize the final shape with the first arm
    final_shape = create_arm()
    
    # Add 3 more arms rotated by 90, 180, and 270 degrees
    for angle in [90, 180, 270]:
        arm = create_arm()
        arm.rotate(angle)
        
        # Boolean OR merges the new arm with the existing structure
        # This creates the smooth, contiguous center
        final_shape = gf.boolean(final_shape, arm, operation="or", layer=layer)
    
    # Add to the main component
    c << final_shape
    
    return c

# Generate and save the device
if __name__ == "__main__":
    device = flower_device()
    device.write_gds("flower_device.gds")
    device.show()