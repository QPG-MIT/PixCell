import gdsfactory as gf

@gf.cell
def device_geometry():
    """
    Constructs the target cross shape by iteratively merging 
    primitive shapes into a single, unified polygon.
    """
    # 1. Start with a central hub
    combined = gf.components.circle(radius=0.5, layer=(1, 0))
    
    # 2. Define the arm and stub as components
    # Using small widths to match the scale of the reference
    arm_shape = gf.components.rectangle(size=(1.0, 0.6), layer=(1, 0), centered=False)
    stub_shape = gf.components.rectangle(size=(0.3, 0.3), layer=(1, 0), centered=False)
    
    for i in range(4):
        # Create a temporary container for the arm+stub to rotate/move them
        part = gf.Component()
        arm = part << arm_shape
        stub = part << stub_shape
        
        # Position them relative to the center
        arm.move((0.5, -0.3))    # Offset from center
        stub.move((1.5, -0.15))  # Move stub to the tip
        
        # Rotate the entire arm assembly
        part.rotate(i * 90)
        
        # 3. Perform the boolean merge
        # This takes the current 'combined' shape and merges it with the new part,
        # returning a new component and avoiding the 'locked' error.
        combined = gf.boolean(combined, part, operation="or", layer=(1, 0))
        
    return combined

# Build and save
device = device_geometry()
device.write_gds("final_shape.gds")
device.show()