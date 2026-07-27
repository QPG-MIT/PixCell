import gdsfactory as gf

@gf.cell
def create_device():
    """
    Creates the device by assembling primitives and then merging them with a
    boolean union operation into a single polygon.
    """
    # Use a temporary component to hold the individual, overlapping shapes
    parts_container = gf.Component("parts")

    # --- 1. Define Dimensions based on Footprint and Proportions ---
    footprint_width = 25.0
    footprint_height = 10.0
    rect_height = 5.0
    prong_total_height = 4.0
    bottom_taper_height = 1.0

    # Prong dimensions
    prong_taper_height = 2.0
    prong_straight_height = 2.0
    prong_base_width = 4.0
    prong_top_width = 2.0
    num_prongs = 4
    prong_gap = (footprint_width - num_prongs * prong_base_width) / (num_prongs - 1)

    # Bottom taper dimensions
    bottom_taper_width_top = 3.0
    bottom_taper_width_bottom = 1.0

    # --- 2. Define Y-coordinates for Vertical Stacking ---
    # Center the entire device footprint at (0, 0) for easier calculations
    y_rect_top = footprint_height / 2 - prong_total_height
    y_rect_bottom = y_rect_top - rect_height

    # --- 3. Create and Place Primitive Components in the Container ---

    # Main rectangular body
    main_body = parts_container << gf.components.rectangle(
        size=(footprint_width, rect_height)
    )
    main_body.ymin = y_rect_bottom
    main_body.x = 0

    # Bottom taper
    bottom_taper = parts_container << gf.components.taper(
        length=bottom_taper_height,
        width1=bottom_taper_width_top,
        width2=bottom_taper_width_bottom,
    )
    bottom_taper.rotate(-90)
    # The taper's origin is at its 'o1' port (the wider end)
    bottom_taper.movey(y_rect_bottom)

    # Define a single prong sub-component for reuse
    @gf.cell
    def prong_unit():
        prong = gf.Component()
        taper_part = prong << gf.components.taper(
            length=prong_taper_height, width1=prong_base_width, width2=prong_top_width
        )
        rect_part = prong << gf.components.rectangle(
            size=(prong_top_width, prong_straight_height)
        )
        taper_part.rotate(90)

        # --- FIX: Manually align instead of using connect ---
        # The connect function fails due to a port type mismatch.
        # We achieve the same placement by manually aligning the rectangle's
        # bottom edge (ymin) to the taper's top port (o2).
        rect_part.x = taper_part.ports["o2"].x
        rect_part.ymin = taper_part.ports["o2"].y
        return prong

    # Place four instances of the prong component
    start_x = -footprint_width / 2 + prong_base_width / 2
    step_x = prong_base_width + prong_gap
    prong_x_positions = [start_x + i * step_x for i in range(num_prongs)]

    prong_template = prong_unit()
    for x_pos in prong_x_positions:
        prong_ref = parts_container << prong_template
        # The prong's origin is at its base. Move it to the top of the main body.
        prong_ref.move((x_pos, y_rect_top))

    # --- 4. Perform Boolean Union ---
    # Create the final component by merging all the placed parts into a single polygon
    final_component = gf.geometry.union(parts_container, by_layer=True, layer=(1, 0))
    return final_component

# --- Main execution block to generate the GDS file ---
if __name__ == "__main__":
    # Instantiate the final device component
    device_to_save = create_device()

    # Write the component to a GDS file.
    device_to_save.write_gds("device.gds")

    # Optionally, show the device in KLayout for visual verification
    print("GDS file 'device.gds' saved successfully.")
    device_to_save.show()