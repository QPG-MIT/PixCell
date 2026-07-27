import gdsfactory as gf

@gf.cell
def create_device():
    """
    Recreates the specified geometry using GDSFactory parametric primitives.

    The device is constructed by defining and assembling three main parts:
    1. A central rectangular body.
    2. A composite "prong" shape, which is then arrayed four times on top.
    3. A tapered feature at the bottom.

    These parts are positioned correctly and then merged using a boolean union
    operation to form the final, single-polygon shape. Dimensions are derived
    from the 25x10 um footprint constraint and visual inspection of the image.
    """
    # --- 1. Define Dimensions based on Footprint and Proportions ---

    # Main body dimensions
    rect_width = 25.0
    rect_height = 5.5

    # Top Prongs: dimensions for a single prong
    prong_taper_length = 1.5
    prong_taper_width_bottom = 3.0
    prong_taper_width_top = 1.5
    prong_straight_length = 2.0

    # Top Prongs: array properties
    num_prongs = 4
    prong_pitch = 6.0

    # Bottom Taper dimensions
    bottom_taper_length = 1.0
    bottom_taper_width_top = 4.0
    bottom_taper_width_bottom = 1.0

    # --- 2. Create Primitive and Composite Components ---

    # Create a composite component for a single top prong
    prong = gf.Component("prong")
    taper_part = prong << gf.components.taper(
        length=prong_taper_length,
        width1=prong_taper_width_bottom,
        width2=prong_taper_width_top,
    )
    straight_part = prong << gf.components.rectangle(
        size=(prong_taper_width_top, prong_straight_length)
    )
    # Align the bottom of the straight part to the top of the taper
    # FIX: The keyword for the target port is 'other', not 'destination'.
    straight_part.connect(port="o4", other=taper_part.ports["o2"])

    # Create the main rectangular body
    main_body = gf.components.rectangle(size=(rect_width, rect_height))

    # Create the bottom tapered feature
    bottom_feature = gf.components.taper(
        length=bottom_taper_length,
        width1=bottom_taper_width_top,
        width2=bottom_taper_width_bottom,
    )

    # --- 3. Assemble Primitives in a Parent Component ---

    # This component will hold all the pieces before the final union
    assembly = gf.Component("assembly")

    # Add the main body. Its vertical position is calculated to ensure
    # the final combined shape is centered at (0,0).
    rect_center_y = -1.25
    body_ref = assembly << main_body
    body_ref.dcenter = (0, rect_center_y)

    # Create and place an array of the prong components
    prong_array = assembly.add_array(
        component=prong,
        columns=num_prongs,
        rows=1,
        spacing=(prong_pitch, 0),
    )
    # Center the entire array horizontally
    prong_array.dcenterx = 0
    # Align the bottom of the prongs with the top edge of the main body
    prong_array.dymin = body_ref.dymax

    # Add and place the bottom feature
    bottom_ref = assembly << bottom_feature
    bottom_ref.drotate(180)  # Point it downwards
    bottom_ref.dcenterx = 0  # Center it horizontally
    # Align its top edge with the bottom edge of the main body
    bottom_ref.dmaxy = body_ref.dymin

    # --- 4. Perform Boolean Union ---

    # Use gf.union to merge all overlapping shapes in the assembly into
    # a single clean polygon, which matches the target image.
    final_device = gf.union(assembly, by_layer=True)

    return final_device

# --- Instantiate the component and write it to a GDS file ---
if __name__ == "__main__":
    # Create an instance of the device by calling the function
    device_to_write = create_device()

    # Write the component to a GDS file named "output.gds"
    device_to_write.write_gds("output.gds")

    # (Optional) Display the component in a viewer to verify the geometry
    device_to_write.show()