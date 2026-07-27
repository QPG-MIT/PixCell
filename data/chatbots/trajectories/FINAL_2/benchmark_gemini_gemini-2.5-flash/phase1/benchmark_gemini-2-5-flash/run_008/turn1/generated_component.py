import gdsfactory as gf

# Define a sub-component for a single chimney
@gf.cell
def single_chimney(
    top_width: float = 2.0,
    top_height: float = 1.5,
    base_width: float = 4.0,
    taper_height: float = 1.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Creates a single chimney component composed of a taper and a rectangle.
    The bottom of the taper (its widest part) is at y=0.
    """
    # Create a temporary component to hold the parts before boolean operation
    c_ch_temp = gf.Component("temp_chimney_parts")

    taper_comp = gf.components.taper(
        length=taper_height,
        width1=top_width,  # The narrower end, which connects to the top rectangle
        width2=base_width, # The wider end, which sits on the main body
        layer=layer
    )
    # Add taper_comp as a reference to c_ch_temp for positioning
    taper_ref = c_ch_temp << taper_comp
    # Move the taper up so its widest part (bottom) is at y=0.
    taper_ref.movey(taper_height / 2)

    rect_comp = gf.components.rectangle(
        size=(top_width, top_height),
        layer=layer,
        centered=True
    )
    # Add rect_comp as a reference to c_ch_temp for positioning
    rect_ref = c_ch_temp << rect_comp
    # Move the rectangle so its bottom edge aligns with the top edge of the taper.
    rect_ref.movey(taper_height + top_height / 2)

    # Union the taper and rectangle to form a single solid chimney shape.
    # gf.boolean returns a new Component.
    united_chimney = gf.boolean(taper_ref, rect_ref, operation="or", layer=layer)

    return united_chimney

@gf.cell
def create_device() -> gf.Component:
    """
    Recreates the geometry from the provided image using GDSFactory parametric functions.
    The device has a footprint of 25um x 10um.
    """
    c = gf.Component("parametric_device")
    layer = (1, 0) # Assuming a single layer for the black geometry

    # --- 1. Main body rectangle ---
    # Based on footprint calculations:
    body_width = 25.0
    body_height = 7.5
    main_body_rect = gf.components.rectangle(size=(body_width, body_height), layer=layer, centered=True)
    # This `main_body_rect` is a Component definition, not yet placed.

    # --- 2. Four chimneys on top ---
    # Parameters for a single chimney
    chimney_top_width = 2.0
    chimney_top_height = 1.5
    chimney_base_width = 4.0
    chimney_taper_height = 1.0

    # Create a template (Component) for a single chimney
    chimney_template = single_chimney(
        top_width=chimney_top_width,
        top_height=chimney_top_height,
        base_width=chimney_base_width,
        taper_height=chimney_taper_height,
        layer=layer
    )

    # Calculate x-positions for the four chimneys (base center)
    x_positions = [-8.25, -2.75, 2.75, 8.25]

    # Chimneys sit on top of the main body. The main body's top edge is at `body_height / 2`.
    chimney_yshift = body_height / 2 # This is 3.75

    # Start the cumulative boolean operation with the main body Component
    current_combined_shape = main_body_rect

    # Place and combine each chimney
    for x_pos in x_positions:
        # Create a temporary Component to hold the chimney reference for correct placement
        # before its geometry is used in the boolean operation.
        temp_chimney_placement = gf.Component("temp_chimney_placement_container")
        chimney_instance_ref = temp_chimney_placement << chimney_template
        chimney_instance_ref.move((x_pos, chimney_yshift))
        
        # Perform boolean OR with the current combined shape (a Component)
        # and the placed chimney instance (a ComponentReference).
        # gf.boolean returns a new Component, which becomes the new current_combined_shape.
        current_combined_shape = gf.boolean(current_combined_shape, chimney_instance_ref, operation="or", layer=layer)

    # --- 3. V-shaped notch at the bottom ---
    notch_width = 5.0
    notch_height = 2.0
    notch_triangle = gf.components.triangle(x=notch_width, y=notch_height, layer=layer)

    # Create a temporary Component for the notch's placement and rotation
    temp_notch_placement = gf.Component("temp_notch_placement_container")
    notch_instance_ref = temp_notch_placement << notch_triangle
    notch_instance_ref.rotate(180) # Rotate to point downwards
    # Move the notch so its base (the top of the V-cut) aligns with the bottom edge of the main body.
    notch_instance_ref.movey(-body_height / 2)

    # --- Perform boolean NOT to cut the notch from the combined shape ---
    # current_combined_shape is a Component (the union of body and chimneys)
    # notch_instance_ref is a ComponentReference (the placed and rotated triangle)
    final_device_component = gf.boolean(current_combined_shape, notch_instance_ref, operation="not", layer=layer)

    # Finally, add the completely constructed geometry (as a Component) to the main component 'c'.
    # This creates a reference to the final geometry within 'c'.
    c << final_device_component

    return c

# Example usage and saving the GDS file
if __name__ == "__main__":
    device = create_device()

    # Optional: Display the device using KLayout (if configured)
    # device.show()

    # Save the device to a GDS file
    device.write_gds("parametric_device.gds")

    # Print bounding box to verify footprint adherence
    bbox = device.bbox
    width = bbox[1][0] - bbox[0][0]
    height = bbox[1][1] - bbox[0][1]
    print(f"Final device bounding box: {bbox}")
    print(f"Calculated width: {width:.2f} um")
    print(f"Calculated height: {height:.2f} um")
    # Expected: width=25.00 um, height=10.00 um