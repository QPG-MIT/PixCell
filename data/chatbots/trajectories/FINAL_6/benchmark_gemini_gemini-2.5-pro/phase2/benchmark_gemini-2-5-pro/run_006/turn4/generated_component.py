import gdsfactory as gf

@gf.cell
def device():
    """
    Creates a symmetrical four-petal cross shape (quatrefoil) with stems.

    This version constructs the shape by creating a single petal-and-stem
    unit and then rotating and unioning it four times. This approach
    correctly models the rounded petals of the target device.

    The construction process is:
    1.  Base shapes (an ellipse for the petal body and a rectangle for the
        stem) are defined.
    2.  A new component (`petal_assembly`) is created. References to the
        base shapes are added to it and moved into their correct positions.
    3.  `gf.union` is used on this assembly to merge the shapes into a single,
        merged petal-and-stem polygon, which is returned as a new component.
    4.  A final assembly component is created. Four references to the merged
        petal unit are added, with each one being rotated by 0, 90, 180,
        and 270 degrees.
    5.  `gf.union` is used again on the four rotated units to
        create the final, symmetrical shape.
    """
    # --- Parameters derived from the target image proportions ---
    TARGET_LAYER = (1, 0)

    # Overall footprint of the final shape
    footprint = 4.7
    # Width of the rectangular stems
    stem_width = 0.35
    # The maximum width of a single petal body
    petal_width = 1.6
    # The length of a petal from the center of the device to the petal tip
    petal_tip_radius = 2.0

    # --- 1. Create a single canonical petal-and-stem unit ---

    # Define the base shapes at the origin (0,0) without transforming them.
    ellipse_radii = (petal_width / 2, petal_tip_radius / 2)
    base_body = gf.components.ellipse(radii=ellipse_radii, layer=TARGET_LAYER)

    stem_top_y = footprint / 2
    stem_bottom_y = petal_tip_radius * 0.85
    stem_length = stem_top_y - stem_bottom_y
    base_stem = gf.components.rectangle(
        size=(stem_width, stem_length), layer=TARGET_LAYER
    )

    # Create a temporary component to assemble one petal.
    # Add references to the base shapes and MOVE THE REFERENCES.
    petal_assembly = gf.Component("petal_assembly")
    body_ref = petal_assembly << base_body
    stem_ref = petal_assembly << base_stem

    # Calculate the required vertical shifts for the references
    ellipse_center_y = petal_tip_radius / 2
    stem_center_y = (stem_top_y + stem_bottom_y) / 2

    # Apply transformations to the references, not the base components
    body_ref.movey(ellipse_center_y)
    stem_ref.movey(stem_center_y)

    # FIX: Use gf.union to merge shapes within the assembly component.
    # This replaces the faulty `gf.boolean(..., B=None, ...)` call.
    merged_petal_unit = gf.union(petal_assembly, by_layer=True)


    # --- 2. Assemble the final four-petal shape by rotation and union ---
    final_assembly = gf.Component("final_assembly")

    # Add four references to the merged petal unit
    ref0 = final_assembly << merged_petal_unit
    ref90 = final_assembly << merged_petal_unit
    ref180 = final_assembly << merged_petal_unit
    ref270 = final_assembly << merged_petal_unit

    # Rotate the references to form the final shape
    ref90.rotate(90)
    ref180.rotate(180)
    ref270.rotate(270)

    # FIX: Perform a final union on the component containing all rotated petals.
    final_shape = gf.union(final_assembly, by_layer=True)


    # Create a new, clean component to hold the final geometry.
    c = gf.Component()
    # Add the final combined shape as a reference and flatten for a clean output.
    _ = c << final_shape
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