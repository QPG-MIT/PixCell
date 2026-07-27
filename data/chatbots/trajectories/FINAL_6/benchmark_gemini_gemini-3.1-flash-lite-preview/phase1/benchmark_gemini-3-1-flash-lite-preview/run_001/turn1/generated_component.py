import gdsfactory as gf

@gf.cell
def star_device():
    """
    Constructs the 4-fold symmetric star geometry using 
    parametric primitives and boolean operations.
    """
    layer = (1, 0)
    
    # 1. Define one 'arm' component
    # The footprint is 4.7um, so radius is 2.35um.
    # Ellipse radius (1.8) + Stem length (0.55) = 2.35um
    arm = gf.Component()
    
    petal = arm << gf.components.ellipse(radii=(1.8, 0.75), layer=layer)
    stem = arm << gf.components.rectangle(size=(0.55, 0.4), layer=layer)
    
    # Align stem to the tip of the ellipse
    # Ellipse tip is at x=1.8. 
    # Rectangle is centered, so we move it to start at x=1.8, y=-0.2 (half height)
    stem.move((1.8, -0.2))

    # 2. Iterate and merge using boolean operations
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