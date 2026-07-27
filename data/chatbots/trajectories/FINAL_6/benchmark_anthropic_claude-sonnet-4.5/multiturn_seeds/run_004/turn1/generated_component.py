import gdsfactory as gf

@gf.cell
def cross_device():
    """
    Creates a cross-shaped device with four elliptical petals.
    Footprint: 4.7 x 4.7 microns
    """
    c = gf.Component()
    
    # Parameters (in microns)
    arm_width = 0.35  # Width of the narrow connecting arms
    petal_width = 1.1  # Width of each petal
    petal_height = 1.4  # Height of each petal
    total_size = 4.7  # Total footprint
    
    # Calculate petal offset from center
    petal_offset = total_size/2 - petal_height/2
    
    # Create horizontal arm (cross member)
    h_arm = gf.components.rectangle(
        size=(total_size, arm_width),
        layer=(1, 0),
        centered=True
    )
    
    # Create vertical arm (cross member)
    v_arm = gf.components.rectangle(
        size=(arm_width, total_size),
        layer=(1, 0),
        centered=True
    )
    
    # Start with the cross base
    result = gf.boolean(h_arm, v_arm, operation="or", layer=(1, 0))
    
    # Create vertical ellipse for top and bottom petals
    petal_vertical = gf.components.ellipse(
        radii=(petal_width/2, petal_height/2),
        layer=(1, 0)
    )
    
    # Top petal
    petal_top = petal_vertical.copy()
    petal_top.move((0, petal_offset))
    result = gf.boolean(result, petal_top, operation="or", layer=(1, 0))
    
    # Bottom petal
    petal_bottom = petal_vertical.copy()
    petal_bottom.move((0, -petal_offset))
    result = gf.boolean(result, petal_bottom, operation="or", layer=(1, 0))
    
    # Create horizontal ellipse for left and right petals
    petal_horizontal = gf.components.ellipse(
        radii=(petal_height/2, petal_width/2),
        layer=(1, 0)
    )
    
    # Right petal
    petal_right = petal_horizontal.copy()
    petal_right.move((petal_offset, 0))
    result = gf.boolean(result, petal_right, operation="or", layer=(1, 0))
    
    # Left petal
    petal_left = petal_horizontal.copy()
    petal_left.move((-petal_offset, 0))
    result = gf.boolean(result, petal_left, operation="or", layer=(1, 0))
    
    # Add final result to component
    c << result
    
    return c

# Create the device
device = cross_device()

# Save to GDS file
device.write_gds("cross_device.gds")

# Optional: Display the device
print("Device created successfully!")
print(f"Bounding box: {device.bbox}")