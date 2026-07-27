import gdsfactory as gf

@gf.cell
def create_swastika_pattern():
    c = gf.Component()
    layer = (1, 0)
    
    # Define cross-section for the paths
    xs = gf.cross_section.cross_section(width=0.5, layer=layer)
    
    # Create top arm (goes right, then down - counter-clockwise bend)
    top_arm_path = gf.Path()
    top_arm_path.append(gf.path.straight(length=1.5))
    top_arm_path.append(gf.path.euler(radius=0.3, angle=-90, p=0.5))  # Counter-clockwise
    top_arm_path.append(gf.path.straight(length=1.5))
    top_arm = gf.path.extrude(top_arm_path, cross_section=xs)
    ref_top = c << top_arm
    ref_top.move((0, 0))
    
    # Create right arm (goes down, then left - counter-clockwise bend)
    right_arm_path = gf.Path()
    right_arm_path.append(gf.path.straight(length=1.5))
    right_arm_path.append(gf.path.euler(radius=0.3, angle=-90, p=0.5))  # Counter-clockwise
    right_arm_path.append(gf.path.straight(length=1.5))
    right_arm = gf.path.extrude(right_arm_path, cross_section=xs)
    ref_right = c << right_arm
    ref_right.rotate(90)
    ref_right.move((0, 0))
    
    # Create bottom arm (goes left, then up - counter-clockwise bend)
    bottom_arm_path = gf.Path()
    bottom_arm_path.append(gf.path.straight(length=1.5))
    bottom_arm_path.append(gf.path.euler(radius=0.3, angle=-90, p=0.5))  # Counter-clockwise
    bottom_arm_path.append(gf.path.straight(length=1.5))
    bottom_arm = gf.path.extrude(bottom_arm_path, cross_section=xs)
    ref_bottom = c << bottom_arm
    ref_bottom.rotate(180)
    ref_bottom.move((0, 0))
    
    # Create left arm (goes up, then right - counter-clockwise bend)
    left_arm_path = gf.Path()
    left_arm_path.append(gf.path.straight(length=1.5))
    left_arm_path.append(gf.path.euler(radius=0.3, angle=-90, p=0.5))  # Counter-clockwise
    left_arm_path.append(gf.path.straight(length=1.5))
    left_arm = gf.path.extrude(left_arm_path, cross_section=xs)
    ref_left = c << left_arm
    ref_left.rotate(270)
    ref_left.move((0, 0))
    
    return c

# Create the device
device = create_swastika_pattern()

# Write to GDS
device.write_gds("swastika_pattern.gds")