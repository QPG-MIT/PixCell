import gdsfactory as gf

@gf.cell
def create_swastika_pattern():
    c = gf.Component()
    layer = (1, 0)
    
    # Define cross-section for the paths
    xs = gf.cross_section.cross_section(width=0.5, layer=layer)
    
    # Create a path for one complete arm of the swastika
    def create_swastika_arm_path():
        path = gf.Path()
        # Start at center, go straight out, then make a 90-degree turn in the same direction for all arms
        path.append(gf.path.straight(length=1.5))  # Go straight out
        path.append(gf.path.euler(radius=0.3, angle=90, p=0.5))  # Make 90-degree turn (clockwise)
        path.append(gf.path.straight(length=1.5))  # Continue in new direction
        return path
    
    # Create the arm shape
    arm_path = create_swastika_arm_path()
    arm_component = gf.path.extrude(arm_path, cross_section=xs)
    
    # Create four instances of the arm, rotated to form the swastika pattern
    # Top-right arm (0 degrees - goes right then down)
    top_right_arm = c << arm_component
    top_right_arm.move((0, 0))
    
    # Bottom-right arm (90 degrees - goes down then left)
    bottom_right_arm = c << arm_component
    bottom_right_arm.rotate(90)
    bottom_right_arm.move((0, 0))
    
    # Bottom-left arm (180 degrees - goes left then up)
    bottom_left_arm = c << arm_component
    bottom_left_arm.rotate(180)
    bottom_left_arm.move((0, 0))
    
    # Top-left arm (270 degrees - goes up then right)
    top_left_arm = c << arm_component
    top_left_arm.rotate(270)
    top_left_arm.move((0, 0))
    
    return c

# Create the device
device = create_swastika_pattern()

# Write to GDS
device.write_gds("swastika_pattern.gds")