import gdsfactory as gf

@gf.cell
def asymmetric_cross():
    """
    Creates an asymmetric, truncated cross shape using boolean operations.

    This device is constructed by the union of two dissimilar "arms", which are
    then truncated at the bottom.
    1. A wide, horizontal ellipse with square tips is defined.
    2. A tall, thin vertical ellipse with a single square tip at its apex is defined.
    3. These two arm components are merged using a boolean 'or' (union) operation.
    4. A large rectangle is used as a "cutter" to remove the bottom portion of the
       unioned shape via a boolean 'not' (subtraction) operation.
    """
    # --- 1. Define Parameters based on visual inspection of the target image ---
    # Horizontal arm (wide and short)
    h_ellipse_radii = (2.0, 1.0)  # (x_radius, y_radius)

    # Vertical arm (thin and tall)
    v_ellipse_radii = (0.6, 2.5)  # (x_radius, y_radius)

    # Square tips at the ends of the arms
    tip_size = 0.4

    # Y-coordinate for the bottom cutoff edge
    truncation_level = -1.5

    # --- 2. Construct the Horizontal Arm ---
    h_arm = gf.Component("horizontal_arm")
    h_arm << gf.components.ellipse(radii=h_ellipse_radii, layer=(1, 0))

    tip_square = gf.components.rectangle(size=(tip_size, tip_size), layer=(1, 0))
    tip_left = h_arm << tip_square
    tip_right = h_arm << tip_square

    # Position tips at the horizontal extents of the ellipse
    tip_left.movex(-h_ellipse_radii[0])
    tip_right.movex(h_ellipse_radii[0])

    # --- 3. Construct the Vertical Arm ---
    v_arm = gf.Component("vertical_arm")
    v_arm << gf.components.ellipse(radii=v_ellipse_radii, layer=(1, 0))
    tip_top = v_arm << tip_square
    tip_top.movey(v_ellipse_radii[1]) # Position tip at the top of the ellipse

    # --- 4. Union the two arms together ---
    unioned_shape = gf.boolean(
        A=h_arm,
        B=v_arm,
        operation="or",
        layer=(1, 0)
    )

    # --- 5. Create a cutter box to truncate the bottom ---
    # The cutter must be large enough to guarantee removal of the bottom part.
    cutter_size = (10, 5) # (width, height) - oversized for safety
    
    # FIX: To position a cached primitive, add it as a reference to a new
    # component, then move the reference.
    cutter_component = gf.Component("cutter_container")
    cutter_base = gf.components.rectangle(size=cutter_size, layer=(1, 0))
    cutter_ref = cutter_component << cutter_base

    # Position the top edge of the cutter *reference* at the truncation level.
    # This will remove everything below this y-coordinate.
    cutter_ref.ymax = truncation_level


    # --- 6. Perform the final subtraction to create the truncated device ---
    final_device = gf.boolean(
        A=unioned_shape,
        B=cutter_component, # Use the component containing the positioned cutter
        operation="not", # 'not' is equivalent to 'A-B'
        layer=(1, 0)
    )

    return final_device

# To display and SAVE the component if the script is run directly
if __name__ == "__main__":
    # Instantiate the component
    c = asymmetric_cross()

    # Display the component in the KLayout viewer (optional, for verification)
    c.show()

    # Save the component to a GDSII file.
    c.write_gds("asymmetric_cross.gds")
    print("GDS file 'asymmetric_cross.gds' saved successfully.")