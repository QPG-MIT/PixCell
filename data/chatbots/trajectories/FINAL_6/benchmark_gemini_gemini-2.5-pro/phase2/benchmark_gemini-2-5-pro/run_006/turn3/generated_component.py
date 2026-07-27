import gdsfactory as gf

@gf.cell
def device():
    """
    Creates a symmetrical four-petal cross shape, often called a quatrefoil
    with stems.

    The shape is constructed methodically using boolean operations:
    1.  Calculates parameters for a 'vesica piscis' (lens shape) to form
        the petals. This shape is the intersection of two circles.
    2.  Creates a vertical lens (top/bottom petals) and a horizontal lens
        (left/right petals).
    3.  Takes the boolean union of these two lenses to form the main
        four-petaled body.
    4.  Creates a standard cross for the stems.
    5.  Takes the final boolean union of the body and the stems.
    """
    # --- Parameters derived from the target image ---
    TARGET_LAYER = (1, 0)

    # Overall footprint of the final shape and the width of the stems
    footprint = 4.7
    stem_width = 0.35

    # Desired dimensions for a single pair of opposing petals (the lens shape).
    # This is the length from tip to tip, excluding the stem.
    petal_pair_length = 4.0
    # This is the maximum width of a single petal.
    petal_width = 1.6

    # --- Calculations for vesica piscis (lens shape from two circles) ---
    # Given the desired length (L) and width (W) of the lens, we solve
    # for the required circle radius (R) and center offset (d).
    L, W = petal_pair_length, petal_width
    if W <= 0:
        raise ValueError("Petal width must be positive.")
    radius = (L**2 + W**2) / (4 * W)
    offset = (L**2 - W**2) / (4 * W)

    # --- Component Construction ---

    # 1. Create the base circle that will be used for intersections.
    base_circle = gf.components.circle(radius=radius, layer=TARGET_LAYER)

    # 2. Create the vertical lens (top and bottom petals) by intersecting
    #    two vertically offset circles.
    vertical_petals = gf.boolean(
        A=base_circle.copy().movey(offset),
        B=base_circle.copy().movey(-offset),
        operation="and",
        layer=TARGET_LAYER,
    )

    # 3. Create the horizontal lens (left and right petals) by intersecting
    #    two horizontally offset circles.
    horizontal_petals = gf.boolean(
        A=base_circle.copy().movex(offset),
        B=base_circle.copy().movex(-offset),
        operation="and",
        layer=TARGET_LAYER,
    )

    # 4. Union the two lenses to form the main four-petaled body.
    body = gf.boolean(
        A=vertical_petals, B=horizontal_petals, operation="or", layer=TARGET_LAYER
    )

    # 5. Create the cross shape for the stems.
    stems = gf.components.cross(length=footprint, width=stem_width, layer=TARGET_LAYER)

    # 6. Union the body and the stems for the final shape.
    final_shape = gf.boolean(A=body, B=stems, operation="or", layer=TARGET_LAYER)

    # Create a new, clean component to hold the final geometry.
    c = gf.Component()
    # Add the final combined shape as a reference.
    _ = c << final_shape
    # Flatten the hierarchy to produce a single, clean polygon set.
    c.flatten()
    return c


# --- Main execution block ---
if __name__ == "__main__":
    # 1. Create an instance of the component defined above.
    my_device_instance = device()

    # 2. (Optional) Display the component in the KLayout viewer.
    my_device_instance.show()

    # 3. Save the component to a GDS file.
    my_device_instance.write_gds("output.gds")