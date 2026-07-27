import gdsfactory as gf

@gf.cell
def custom_petal_cross(
    taper_length: float = 1.55,
    taper_width_in: float = 0.3,  # Width of the taper at the stem connection end
    taper_width_out: float = 1.2, # Maximum width of the taper (towards the center)
    stem_length: float = 0.8,
    stem_width: float = 0.3,      # Width of the straight rectangular stem
    center_circle_radius: float = 0.6, # Radius of the central circle
    layer: gf.typings.LayerSpec = (1, 0)
) -> gf.Component:
    """
    Creates a 4-fold rotationally symmetric cross-like shape with
    curved "petal" arms and straight "stem" tips.

    The shape is constructed by:
    1. Defining parameters that visually match the input image and footprint.
    2. Creating a base "arm" consisting of a taper (wide end towards the center)
       and a straight rectangular stem.
    3. Instantiating and rotating this arm four times to form the cross.
    4. Placing a central circle at the origin to round off the center where arms meet.
    5. Performing a boolean OR operation to merge all overlapping shapes into a single polygon.

    Args:
        taper_length: Length of the tapered section of each arm.
        taper_width_in: Width of the taper where it connects to the stem. This should
                        match `stem_width` for a smooth transition.
        taper_width_out: Maximum width of the taper (towards the center).
        stem_length: Length of the straight rectangular stem.
        stem_width: Width of the straight rectangular stem. It is internally
                    enforced to be equal to `taper_width_in` for consistency.
        center_circle_radius: Radius of the circle at the very center of the cross.
                              This helps to round off the central junction.
        layer: GDS layer for the geometry (e.g., (1, 0) for primary layer).
    """
    c = gf.Component()

    # Ensure stem_width matches taper_width_in for a smooth transition
    stem_width = taper_width_in

    # 1. Create the base components (one taper and one stem)
    # The taper component will be created such that its `width1` (wide end) is at x=0
    # and it extends in the +X direction to `taper_length` where its `width2` (narrow end) is.
    taper_base = gf.components.taper(
        length=taper_length,
        width1=taper_width_out,  # Wide end towards the intended rotation origin (0,0)
        width2=taper_width_in,   # Narrow end is at (taper_length, 0)
        layer=layer,
    )

    # The stem component is a simple rectangle.
    # It will be created such that its bottom-left corner is at (0,0) and extends positive.
    stem_base = gf.components.rectangle(
        size=(stem_width, stem_length),
        layer=layer,
        centered=False
    )

    # 2. Build one complete arm component (taper + stem)
    # This 'one_arm_proto' component will have its origin (0,0) at the wide end of the taper
    # and extend vertically upwards (+Y).
    one_arm_proto = gf.Component("petal_arm_vertical_prototype")
    
    # Add the taper to the prototype arm. Rotate it 90 degrees so it points upwards.
    # After rotation, its wide end (width_out) will be centered at (0,0),
    # and it extends to (0, taper_length) where its narrow end (width_in) is, also centered on x=0.
    taper_ref_proto = one_arm_proto << taper_base
    taper_ref_proto.rotate(90) 
    
    # Add the stem to the prototype arm.
    # Move it such that its bottom-center aligns with the taper's top-center.
    stem_ref_proto = one_arm_proto << stem_base
    stem_ref_proto.movex(-stem_width / 2) # Center the stem horizontally on the Y-axis
    stem_ref_proto.movey(taper_length)    # Place the stem directly on top of the taper

    # 3. Add four instances of the 'one_arm_proto' component to the main component `c`.
    # Each 'c << ...' operation creates a new reference.
    # We apply rotations to these references to form the cross.

    # Arm 1: Extends +Y (no rotation needed for this instance relative to 'one_arm_proto' definition)
    c << one_arm_proto

    # Arm 2: Extends +X
    arm2_ref = c << one_arm_proto
    arm2_ref.rotate(angle=-90) # Rotate clockwise 90 degrees (points right)

    # Arm 3: Extends -Y
    arm3_ref = c << one_arm_proto
    arm3_ref.rotate(angle=180) # Rotate 180 degrees (points down)

    # Arm 4: Extends -X
    arm4_ref = c << one_arm_proto
    arm4_ref.rotate(angle=90)  # Rotate counter-clockwise 90 degrees (points left)

    # 4. Add the central circle to `c`.
    # This circle is centered at (0,0), perfectly aligning with the meeting point of the tapers.
    # It helps to round off the inner corners formed by the four tapers.
    c << gf.components.circle(radius=center_circle_radius, layer=layer)

    # 5. Perform a boolean OR operation to merge all overlapping shapes within 'c'.
    # gf.boolean(A, operation="or") will take all polygons and references within Component A
    # and perform a union operation, returning a new component with the merged geometry.
    merged_shape_comp = gf.boolean(c, operation="or", layer=layer)
    
    # Clear the original component 'c' of all its individual references and polygons.
    c.clear() 
    
    # Add the single, unified merged shape to 'c'.
    c.add_ref(merged_shape_comp)

    # Verify the footprint of the generated device
    # The total length from the center to the tip of one arm is taper_length + stem_length.
    # So, the total width/height of the bounding box will be 2 * (taper_length + stem_length).
    expected_footprint_dimension = 2 * (taper_length + stem_length)
    print(f"Calculated device dimension: {expected_footprint_dimension:.1f} x {expected_footprint_dimension:.1f} um")

    return c

if __name__ == "__main__":
    # Create the component with parameters chosen to match the image and footprint
    # Footprint: [4.7, 4.7] um
    # Calculated: 2 * (1.55 + 0.8) = 2 * 2.35 = 4.7 um
    device = custom_petal_cross(
        taper_length=1.55,
        taper_width_in=0.3,
        taper_width_out=1.2,
        stem_length=0.8,
        stem_width=0.3, # This value is enforced to be taper_width_in inside the function
        center_circle_radius=0.6,
        layer=(1, 0)
    )

    # Write the GDS file
    device.write_gds("petal_cross_device.gds")

    # Optional: Display the component (requires KLayout or similar viewer setup for GDSFactory)
    # gf.show(device)