import gdsfactory as gf
import os

@gf.cell
def create_petal_cross(
    size: float = 4.7,
    petal_width: float = 2.6,
    stem_width: float = 0.4,
    layer: tuple = (1, 0),
):
    """
    Creates a symmetrical four-lobed shape resembling a flower or a cross
    with leaf-shaped arms.

    This shape is constructed by the boolean union of three components:
    1. A vertical ellipse to form the top and bottom petals.
    2. A horizontal ellipse to form the left and right petals.
    3. A standard cross shape to form the rectangular stems at the four tips.

    Args:
        size: The total width and height of the component.
        petal_width: The maximum width of each of the four curved petals. A larger
                     value makes the petals "fatter".
        stem_width: The width of the rectangular stems at the tips.
        layer: The GDS layer for the component.
    """
    c = gf.Component()

    # The major axis of the ellipses corresponds to half the total component size.
    ellipse_major_radius = size / 2.0
    
    # The minor axis of the ellipses is determined by the desired petal width.
    ellipse_minor_radius = petal_width / 2.0

    # 1. Create the vertical and horizontal ellipses that form the petals.
    vertical_petals = gf.components.ellipse(
        radii=(ellipse_minor_radius, ellipse_major_radius), layer=layer
    )
    horizontal_petals = gf.components.ellipse(
        radii=(ellipse_major_radius, ellipse_minor_radius), layer=layer
    )

    # 2. Union the two ellipses to form the main four-petaled body.
    body = gf.boolean(A=vertical_petals, B=horizontal_petals, operation="or", layer=layer)

    # 3. Create a cross shape for the stems. The cross's total length matches the
    #    component size, and its arm width defines the stem thickness.
    stems = gf.components.cross(length=size, width=stem_width, layer=layer)

    # 4. Union the petaled body with the stems to get the final, complete shape.
    final_shape = gf.boolean(A=body, B=stems, operation="or", layer=layer)

    # Add the final combined geometry as a single polygon set to the component.
    _ = c << final_shape
    c.info['footprint_um'] = (size, size)

    return c

# --- Instantiate and Save the Component ---
if __name__ == "__main__":
    # Parameters are estimated from the target image to match its appearance,
    # adhering to the 4.7x4.7 um footprint constraint.
    # - `petal_width` is tuned to make the arms look appropriately full.
    # - `stem_width` creates the small rectangular features at the ends.
    device = create_petal_cross(
        size=4.7,
        petal_width=2.6,
        stem_width=0.4
    )

    # Define the output filename
    output_filename = "petal_cross.gds"
    
    # Write the GDS file
    device.write_gds(output_filename)
    
    # Add a confirmation message for the user
    print(f"Successfully wrote GDS file to: {os.path.abspath(output_filename)}")

    # To display the component if running interactively
    # device.show()