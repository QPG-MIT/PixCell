import gdsfactory as gf

@gf.cell
def star_cross_device():
    """
    Creates a 4-fold symmetric device with elliptical petals and rectangular tips.
    Footprint constrained to 4.7um x 4.7um.
    """
    c = gf.Component()
    
    # ---------------------------
    # 1. Define Dimensions
    # ---------------------------
    target_footprint = 4.7
    radius = target_footprint / 2.0  # 2.35 um
    
    # Petal (Main elliptical body)
    petal_len = 1.9
    petal_width = 0.85
    
    # Stub (Rectangular tip)
    stub_len = 0.5
    stub_width = 0.18
    
    # ---------------------------
    # 2. Construct Single Arm
    # ---------------------------
    # We build the arm horizontally along the X-axis.
    # We use a temporary component to assemble the primitives before boolean union.
    arm_temp = gf.Component()
    
    # Create Petal (Ellipse)
    # gf.components.ellipse creates an ellipse centered at (0,0).
    # We shift it by half its length so it starts at x=0 and extends to x=petal_len.
    e = arm_temp << gf.components.ellipse(radii=(petal_len/2, petal_width/2), layer=(1, 0))
    e.move((petal_len/2, 0))
    
    # Create Stub (Rectangle)
    # We position the stub so it ends exactly at the target radius (2.35).
    # Center position = Radius - (Stub_Length / 2)
    s = arm_temp << gf.components.rectangle(size=(stub_len, stub_width), layer=(1, 0), centered=True)
    s.move((radius - stub_len/2, 0))
    
    # Merge primitives into a single polygon for the arm
    # This ensures the arm is one continuous shape.
    arm_shape = gf.boolean(e, s, operation="or", layer=(1, 0))
    
    # ---------------------------
    # 3. Assemble Full Device
    # ---------------------------
    # Add 4 rotated copies of the arm to the main component
    for angle in [0, 90, 180, 270]:
        ref = c << arm_shape
        ref.rotate(angle)
        
    return c

if __name__ == "__main__":
    # Generate the device
    device = star_cross_device()
    
    # Output statistics
    print(f"Device size: {device.size_info.width} x {device.size_info.height}")
    
    # Save and Show
    device.write_gds("star_cross_device.gds")
    device.show()