import gdsfactory as gf

@gf.cell
def four_leaf_clover():
    c = gf.Component()
    
    # Define parameters based on footprint (4.7um x 4.7um)
    total_size = 4.7
    arm_length = total_size / 2  # 2.35um from center to end
    arm_width = 1.0              # estimated width
    layer = (1, 0)               # default layer
    
    # Create a cross-section for the arms
    xs = gf.cross_section.cross_section(width=arm_width, layer=layer)
    
    # Create each arm using a path with circular arcs for the curved ends
    def create_arm_path():
        # Create a path that goes straight, then curves to form the petal shape
        path = gf.Path()
        # Start with a straight segment
        path.append(gf.path.straight(length=arm_length/2))
        # Add a circular arc to create the curved end (quarter circle)
        path.append(gf.path.arc(radius=arm_width/2, angle=90))
        # Add another straight segment back
        path.append(gf.path.straight(length=arm_length/2))
        # Add another circular arc to close the shape
        path.append(gf.path.arc(radius=arm_width/2, angle=90))
        
        return path
    
    # Create one arm (right)
    arm1_path = create_arm_path()
    arm1 = gf.path.extrude(arm1_path, cross_section=xs)
    arm1_ref = c << arm1
    arm1_ref.move((arm_length/2, 0))
    arm1_ref.rotate(90)  # Point right
    
    # Create second arm (top)
    arm2_path = create_arm_path()
    arm2 = gf.path.extrude(arm2_path, cross_section=xs)
    arm2_ref = c << arm2
    arm2_ref.move((0, arm_length/2))
    arm2_ref.rotate(0)  # Point up
    
    # Create third arm (left)
    arm3_path = create_arm_path()
    arm3 = gf.path.extrude(arm3_path, cross_section=xs)
    arm3_ref = c << arm3
    arm3_ref.move((-arm_length/2, 0))
    arm3_ref.rotate(270)  # Point left
    
    # Create fourth arm (bottom)
    arm4_path = create_arm_path()
    arm4 = gf.path.extrude(arm4_path, cross_section=xs)
    arm4_ref = c << arm4
    arm4_ref.move((0, -arm_length/2))
    arm4_ref.rotate(180)  # Point down
    
    return c

# Create and save the device
device = four_leaf_clover()
device.write_gds("four_leaf_clover.gds")