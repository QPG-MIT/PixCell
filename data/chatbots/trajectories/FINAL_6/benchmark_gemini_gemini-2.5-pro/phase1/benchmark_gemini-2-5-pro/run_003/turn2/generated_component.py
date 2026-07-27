import gdsfactory as gf
import pathlib

@gf.cell
def create_device():
    """
    Creates a four-lobed, rounded shape with stems, matching the target image.

    The geometry is constructed by the boolean union of two main parts:
    1. A central "bulbous" body. This is created by the union of two very "fat"
       ellipses (where the minor axis is close in length to the major axis).
       This approach ensures the smooth, rounded transitions between the lobes,
       which is a key feature of the target image.
    2. A "stem" shape, created with the `gf.components.cross` primitive. This
       defines the overall footprint and adds the small rectangular protrusions.
    """

    # --- Parameters ---
    # Derived from the footprint constraint and visual analysis of the new image.

    # The total width and height of the device, from the footprint constraint.
    footprint_size = 4.7  # um

    # The width of the stems, estimated visually.
    stem_width = 0.4  # um

    # --- Ellipse parameters for the rounded central body ---
    # To create the "bulbous" look, the ellipses need to be very fat,
    # almost circular. We make the minor radius large relative to the major radius.
    
    # Major radius: controls the extent of the lobes.
    # Set to be less than half the footprint to allow stems to be visible.
    major_radius = 2.2  # um

    # Minor radius: controls the "fatness" of the lobes. A larger value
    # creates the rounded, bulbous shape seen in the target image.
    minor_radius = 1.8  # um
    
    # Define the GDS layer for the geometry.
    layer = (1, 0)

    # --- Geometry Construction ---

    # 1. Create the central rounded body by unioning two fat ellipses.
    
    # Create a vertically oriented fat ellipse.
    ellipse_vertical = gf.components.ellipse(
        radii=(minor_radius, major_radius), # (short_axis, long_axis)
        layer=layer
    )

    # Create a horizontally oriented fat ellipse.
    ellipse_horizontal = gf.components.ellipse(
        radii=(major_radius, minor_radius), # (long_axis, short_axis)
        layer=layer
    )

    # Perform a boolean 'or' (union) to merge the ellipses. The result is a
    # single, smooth, rounded quatrefoil shape.
    central_body = gf.boolean(
        A=ellipse_vertical,
        B=ellipse_horizontal,
        operation="or",
        layer=layer
    )

    # 2. Create the stem shape using the cross primitive.
    stems = gf.components.cross(
        length=footprint_size,
        width=stem_width,
        layer=layer
    )

    # 3. Combine the central body and the stems into the final shape.
    final_shape = gf.boolean(
        A=central_body,
        B=stems,
        operation="or",
        layer=layer
    )

    # --- Final Component Assembly ---

    # Create a new, empty component to hold the final geometry.
    c = gf.Component("rounded_cross_device")

    # Add the combined shape as a reference.
    c.add_ref(final_shape)

    return c

# This block allows the script to be run directly to generate and view the GDS.
if __name__ == "__main__":
    # Instantiate the component by calling the decorated function.
    device = create_device()

    # Use the show() method to open the component in the KLayout viewer.
    device.show()
    
    # Print the component's bounding box size to verify it matches the footprint.
    print(f"Component created: {device.name}")
    print(f"Bounding box size (width, height): ({device.xsize}, {device.ysize})")
    print(f"Expected footprint: [{4.7}, {4.7}]")
    
    # Get the directory of the current script
    script_dir = pathlib.Path(__file__).parent.resolve()
    # Define the output file path
    output_gds_path = script_dir / "output.gds"
    device.write_gds(output_gds_path)
    print(f"GDS file saved to: {output_gds_path}")