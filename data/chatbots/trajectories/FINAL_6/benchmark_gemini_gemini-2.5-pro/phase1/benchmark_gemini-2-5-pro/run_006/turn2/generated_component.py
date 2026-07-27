import gdsfactory as gf

@gf.cell
def device():
    """
    Creates an asymmetric four-petal cross shape using parametric GDSFactory
    components and boolean operations.

    The shape is constructed by taking the union of a wide horizontal ellipse,
    a tall vertical ellipse, and an asymmetric cross formed from two rectangles.
    """
    # --- Parameters derived from the new target image ---

    # Define the GDS layer for all geometry.
    TARGET_LAYER = (1, 0)

    # Define the overall asymmetric footprint
    footprint_x = 4.2
    footprint_y = 5.8
    stem_width = 0.3

    # Parameters for the wide, short ellipse (forms horizontal arms)
    # Radii are (x_radius, y_radius)
    ellipse_h_radii = (1.9, 1.6)

    # Parameters for the tall, narrow ellipse (forms vertical arms)
    ellipse_v_radii = (1.2, 2.7)

    # --- Component Creation and Assembly ---

    # 1. Create an asymmetric cross for the stems using two rectangles.
    stem_horizontal = gf.components.rectangle(
        size=(footprint_x, stem_width), layer=TARGET_LAYER
    )
    stem_vertical = gf.components.rectangle(
        size=(stem_width, footprint_y), layer=TARGET_LAYER
    )
    stem_cross = gf.boolean(
        A=stem_horizontal, B=stem_vertical, operation="or", layer=TARGET_LAYER
    )

    # 2. Create the two different ellipses for the asymmetric petals.
    ellipse_horizontal = gf.components.ellipse(
        radii=ellipse_h_radii, layer=TARGET_LAYER
    )
    ellipse_vertical = gf.components.ellipse(
        radii=ellipse_v_radii, layer=TARGET_LAYER
    )

    # 3. Perform boolean 'or' (union) operations to combine the shapes.
    #    First, union the two different ellipses to create the main body.
    body = gf.boolean(
        A=ellipse_horizontal, B=ellipse_vertical, operation="or", layer=TARGET_LAYER
    )

    #    Second, union the body with the asymmetric cross to add the stems.
    final_shape = gf.boolean(
        A=body, B=stem_cross, operation="or", layer=TARGET_LAYER
    )

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