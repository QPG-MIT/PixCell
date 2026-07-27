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
    
    # Create each arm using a path with circular arcs for smooth curvature
    def create_arm():
        # Create a path that forms a smooth, curved arm
        path = gf.Path()
        
        # Use a combination of straight segments and circular arcs to create a smooth curve
        # This creates a more natural curved shape
        path.append(gf.path.straight(length=arm_length/4))
        path.append(gf.path.arc(radius=arm_width/2, angle=90))
        path.append(gf.path.straight(length=arm_length/4))
        
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