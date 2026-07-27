import gdsfactory as gf

@gf.cell
def device_flower() -> gf.Component:
    """
    Creates a symmetrical flower-like cross shape using GDSFactory parametric functions.

    The shape consists of four identical arms, each composed of a straight tip,
    a tapering section from max width to tip width, and another tapering section
    from center width to max width. These sections are generated using path
    extrusions with parabolic transitions, and then combined using boolean OR operations.
    """
    c = gf.Component("flower_cross_assembly")

    # Define overall dimensions from the footprint constraint
    overall_length = 4.7  # Total length/width of the device in um
    half_length = overall_length / 2.0  # Half length from center to tip (2.35 um)

    # --- Parameters for one arm's geometry (visual estimations from image) ---
    # Widths in um
    width_tip = 0.5            # Width of the straight segment at the very end
    width_center = 0.4         # Width at the center point where the four arms meet
    width_max = 1.0            # Maximum width of the rounded/petal part of the arm

    # Lengths in um for different sections of the arm
    length_tip = 0.4           # Length of the straight tip segment

    # Calculate remaining length for the two tapering sections (L1 and L2)
    remaining_taper_length = half_length - length_tip # 2.35 - 0.4 = 1.95 um

    # Length from the center to the point of maximum width (L1)
    # Estimated to be closer to the center than to the tip
    length_L1 = 0.8 # um

    # Length from the point of maximum width to the start of the tip segment (L2)
    length_L2 = remaining_taper_length - length_L1 # 1.95 - 0.8 = 1.15 um

    # --- Create a single parametric arm component (`single_petal_arm`) ---
    # This component will be generated from (0,0) along the +X axis
    arm_component = gf.Component("single_petal_arm")

    # Define cross_sections for the start, middle (max width), and end of the transitions
    xs_center = gf.cross_section.cross_section(width=width_center, layer=(1, 0))
    xs_max = gf.cross_section.cross_section(width=width_max, layer=(1, 0))
    xs_tip = gf.cross_section.cross_section(width=width_tip, layer=(1, 0))

    # Path segment 1: From center width to max width point
    # Path starts at (0,0) of `arm_component`
    path1 = gf.path.straight(length=length_L1)
    transition1 = gf.path.transition(xs_center, xs_max, width_type='parabolic')
    petal_section1 = gf.path.extrude_transition(path1, transition1)
    ref1 = arm_component << petal_section1

    # Path segment 2: From max width point to the start of the straight tip
    path2 = gf.path.straight(length=length_L2)
    transition2 = gf.path.transition(xs_max, xs_tip, width_type='parabolic')
    petal_section2 = gf.path.extrude_transition(path2, transition2)
    ref2 = arm_component << petal_section2
    # Connect this segment to the end of the previous one
    ref2.connect("o1", ref1.ports["o2"])

    # Path segment 3: The straight tip section
    path3 = gf.path.straight(length=length_tip)
    straight_tip_section = gf.path.extrude(path3, xs_tip)
    ref3 = arm_component << straight_tip_section
    # Connect this segment to the end of the previous one
    ref3.connect("o1", ref2.ports["o2"])

    # --- Assemble the four arms using rotation and boolean operations ---

    # Create a list to hold the rotated component references
    # These references will be used for the boolean operation but not yet added to 'c'
    arms_for_boolean_ops = []

    # 1. Right arm (0 degrees rotation)
    ref_right = arm_component.ref() # Create a ComponentReference for arm_component
    ref_right.rotate(angle=0) # Rotate the reference
    arms_for_boolean_ops.append(ref_right)

    # 2. Top arm (90 degrees rotation)
    ref_top = arm_component.ref()
    ref_top.rotate(angle=90)
    arms_for_boolean_ops.append(ref_top)

    # 3. Left arm (180 degrees rotation)
    ref_left = arm_component.ref()
    ref_left.rotate(angle=180)
    arms_for_boolean_ops.append(ref_left)

    # 4. Bottom arm (-90 degrees rotation)
    ref_bottom = arm_component.ref()
    ref_bottom.rotate(angle=-90)
    arms_for_boolean_ops.append(ref_bottom)

    # Perform iterative boolean OR operation
    if not arms_for_boolean_ops:
        return c # Return empty component if no arms were created

    # Start with the first reference for the boolean operation.
    # gf.boolean can take ComponentReferences as inputs.
    merged_component = arms_for_boolean_ops[0]

    # Iterate through the rest and apply boolean OR
    for i in range(1, len(arms_for_boolean_ops)):
        # Each call to gf.boolean will return a new gf.Component (or reference, depending on internal logic)
        # ensuring 'merged_component' remains a valid object for subsequent boolean calls.
        merged_component = gf.boolean(merged_component, arms_for_boolean_ops[i], operation="or", layer=(1, 0))

    # Add the final merged component to the main component 'c'
    c << merged_component

    # Flatten the component to remove nested references and obtain a clean set of polygons
    c.flatten()

    return c

# --- Script execution for testing and GDS generation ---
if __name__ == "__main__":
    flower_device = device_flower()

    # Verify the generated device footprint against the constraint
    bbox = flower_device.bbox
    actual_width = bbox[1][0] - bbox[0][0]
    actual_height = bbox[1][1] - bbox[0][1]
    expected_footprint = [4.7, 4.7]

    print(f"Generated device footprint: {actual_width:.2f} x {actual_height:.2f} um")
    print(f"Expected device footprint: {expected_footprint[0]:.2f} x {expected_footprint[1]:.2f} um")

    # Write the GDS file
    flower_device.write_gds("flower_cross.gds")

    # Optional: Display the component (requires KLayout or other GDS viewer configuration)
    # gf.show(flower_device)