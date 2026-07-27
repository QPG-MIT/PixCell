import gdsfactory as gf

@gf.cell
def star_device():
    """
    Recreates the star/cross geometry by overlapping 4 'arm' components 
    consisting of a fat ellipse and a rectangular stem.
    """
    layer = (1, 0)
    
    # 1. Define the 'arm' component
    arm = gf.Component()
    
    # Use a fatter ellipse (shorter x, wider y) to ensure a solid central core
    # Radii=(1.3, 1.0) creates a much fuller petal shape
    petal = arm << gf.components.ellipse(radii=(1.3, 1.0), layer=layer)
    
    # Shift the petal center so it overlaps at the origin (0,0)
    # The petal is 1.3 units long; moving it 0.6 units out ensures the 
    # inner half sits inside the center, creating the central hub.
    petal.move((0.6, 0))
    
    # Add a stem at the tip of the petal
    # The tip of the petal is at x = 0.6 + 1.3 = 1.9
    stem = arm << gf.components.rectangle(size=(0.5, 0.4), layer=layer, centered=True)
    stem.move((1.9, 0))

    # 2. Iterate, rotate, and merge using boolean operations
    final_shape = None
    
    for angle in [0, 90, 180, 270]:
        # Create a container for the rotated arm
        rotated_arm = gf.Component()
        ref = rotated_arm << arm
        ref.rotate(angle)
        
        # Merge with previous shapes using boolean OR
        if final_shape is None:
            final_shape = rotated_arm
        else:
            final_shape = gf.boolean(
                final_shape, 
                rotated_arm, 
                operation="or", 
                layer=layer
            )
            
    return final_shape

# Create and save the device
if __name__ == "__main__":
    device = star_device()
    device.write_gds("star_device.gds")
    print("GDS file 'star_device.gds' produced successfully.")