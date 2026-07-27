import gdsfactory as gf

@gf.cell
def four_leaf_clover():
    c = gf.Component()
    
    # Define parameters based on footprint (4.7um x 4.7um)
    total_size = 4.7
    arm_length = total_size / 2  # 2.35um from center to end
    arm_width = 1.0              # width of each arm
    layer = (1, 0)               # default layer
    
    # Create a cross-section for the arms
    xs = gf.cross_section.cross_section(width=arm_width, layer=layer)
    
    # Create each arm using a smooth path for curved leaf shape
    def create_arm():
        # Define waypoints for a smooth leaf-like curve
        # Start at origin, curve outward, then back to end point
        waypoints = [
            (0, 0),  # Start at center
            (arm_length * 0.3, arm_length * 0.2),  # Control point 1
            (arm_length * 0.7, arm_length * 0.2),  # Control point 2
            (arm_length, 0)  # End point
        ]
        
        # Create smooth path from waypoints
        path = gf.path.smooth(points=waypoints, radius=arm_width * 0.5)
        
        # Extrude the path
        arm = gf.path.extrude(path, cross_section=xs)
        return arm
    
    # Create the four arms
    arm1 = create_arm()  # Right arm
    arm2 = create_arm()  # Top arm
    arm3 = create_arm()  # Left arm
    arm4 = create_arm()  # Bottom arm
    
    # Add to main component with proper positioning and rotation
    arm1_ref = c << arm1
    arm1_ref.rotate(0)  # Point right
    
    arm2_ref = c << arm2
    arm2_ref.rotate(90)   # Point up
    
    arm3_ref = c << arm3
    arm3_ref.rotate(180) # Point left
    
    arm4_ref = c << arm4
    arm4_ref.rotate(270) # Point down
    
    return c

# Create and save the device
device = four_leaf_clover()
device.write_gds("four_leaf_clover.gds")