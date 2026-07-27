import gdsfactory as gf

@gf.cell
def create_device():
    """
    Recreates the specified device geometry using GDSFactory parametric primitives
    and boolean operations.

    The shape is constructed by taking the boolean union of two underlying shapes:
    1. A simple rectangular cross, which forms the straight "stems" at the tips.
    2. A four-petal flower shape, created by the union of a horizontal and a
       vertical ellipse. This forms the main curved body of the arms.

    The parameters are chosen to match the target footprint of 4.7x4.7 um.
    """
    # --- Define Parameters ---
    # Overall dimension is derived from the 4.7x4.7um footprint.
    footprint_dim = 4.7

    # Parameters for the rectangular cross (forms the straight tips).
    # The 'length' of the cross defines the total extent of the final shape.
    cross_length = footprint_dim
    # The 'width' is estimated visually from the image.
    cross_width = 0.5

    # Parameters for the petal shape (made from two overlapping ellipses).
    # The major radius is slightly less than half the total length, allowing
    # the rectangular cross tips to extend beyond the curved part.
    petal_major_radius = 2.1
    # The minor radius determines the "fatness" of the petals.
    petal_minor_radius = 1.15

    # GDS layer for the geometry.
    layer = (1, 0)

    # --- Component Assembly ---
    # Create a parent component to hold the final geometry.
    c = gf.Component("recreated_device")

    # 1. Create the base rectangular cross.
    # This primitive is centered at (0,0) by default.
    rect_cross = gf.components.cross(
        length=cross_length,
        width=cross_width,
        layer=layer
    )

    # 2. Create the four-petal flower shape from two ellipses.
    # A horizontal ellipse.
    ellipse_h = gf.components.ellipse(
        radii=(petal_major_radius, petal_minor_radius),
        layer=layer
    )
    # A vertical ellipse.
    ellipse_v = gf.components.ellipse(
        radii=(petal_minor_radius, petal_major_radius),
        layer=layer
    )
    # Combine the two ellipses using a boolean "OR" (union) operation.
    # The result is a new Component containing the four-petal shape.
    petals = gf.boolean(
        A=ellipse_h,
        B=ellipse_v,
        operation="or",
        layer=layer
    )

    # 3. Combine the rectangular cross and the petal shape.
    # The final shape is the union of the two previously created components.
    # Since all primitives were centered at the origin, the boolean operation
    # aligns them correctly.
    final_shape = gf.boolean(
        A=rect_cross,
        B=petals,
        operation="or",
        layer=layer
    )

    # Add a reference to the final combined geometry into the parent component.
    c << final_shape

    return c

# --- Main Execution Block ---
if __name__ == "__main__":
    # Instantiate the component.
    device = create_device()

    # Optional: Display the component in a KLayout window to verify.
    device.show()

    # Optional: Print the component's dimensions to verify against the footprint.
    # FIX: The '.size' attribute is deprecated or not available in all gdsfactory
    # backends (like kfactory). The correct way to get dimensions is via
    # the '.size_info' attribute, which holds 'width' and 'height' properties.
    print(f"Component size (width, height): ({device.size_info.width}, {device.size_info.height})")


    # Optional: Save the component to a GDS file.
    # device.write_gds("recreated_device.gds")