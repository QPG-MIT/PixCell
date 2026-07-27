import gdsfactory as gf

@gf.cell
def create_device():
    """
    Recreates the device from the provided image using parametric gdsfactory
    components and boolean operations, fitting within a 25x10 um footprint.

    The geometry is built by creating individual primitive shapes (rectangles,
    tapers), placing them in their correct relative positions, and then
    performing a single union operation to merge them into a monolithic polygon.
    """
    # --- Define Device Parameters ---
    # These parameters are derived from the overall footprint [25, 10] um and
    # the visual proportions of the features in the provided image.

    # Main body dimensions
    main_rect_width = 25.0
    main_rect_height = 4.0

    # Top tower dimensions and parameters
    tower_taper_height = 2.5
    tower_straight_height = 2.5
    tower_base_width = 4.0
    tower_top_width = 1.5

    # Spacing for top towers, centered symmetrically
    tower_x_positions = [-9.0, -3.0, 3.0, 9.0]

    # Bottom tab dimensions
    bottom_tab_height = 1.0
    bottom_tab_width_top = 5.0
    bottom_tab_width_bottom = 2.0

    # Layer for all geometry
    layer = (1, 0)

    # --- Create a list to hold each geometric part for the union ---
    parts = []

    # 1. Main Body (centered at the origin)
    main_body_shape = gf.components.rectangle(
        size=(main_rect_width, main_rect_height), centered=True, layer=layer
    )
    parts.append(main_body_shape)

    # 2. Bottom Tab
    # Create a temporary component to correctly place the tab
    tab_component = gf.Component("bottom_tab_placed")
    tab_primitive = gf.components.taper(
        length=bottom_tab_height,
        width1=bottom_tab_width_top,
        width2=bottom_tab_width_bottom,
        layer=layer,
    )
    tab_ref = tab_component << tab_primitive
    tab_ref.rotate(-90)
    tab_ref.movey(-main_rect_height / 2 - bottom_tab_height / 2)
    parts.append(tab_component)

    # 3. Top Towers
    # Create the primitive shapes once to be referenced in the loop
    tower_taper_primitive = gf.components.taper(
        length=tower_taper_height,
        width1=tower_base_width,
        width2=tower_top_width,
        layer=layer,
    )
    tower_straight_primitive = gf.components.rectangle(
        size=(tower_top_width, tower_straight_height), centered=True, layer=layer
    )

    for x in tower_x_positions:
        # Create a temporary component for each tower part to position it
        
        # Taper part of the tower
        taper_part_component = gf.Component()
        taper_ref = taper_part_component << tower_taper_primitive
        taper_ref.rotate(90)
        taper_ref.move((x, main_rect_height / 2 + tower_taper_height / 2))
        parts.append(taper_part_component)

        # Straight part of the tower
        straight_part_component = gf.Component()
        straight_ref = straight_part_component << tower_straight_primitive
        straight_ref.move(
            (x, main_rect_height / 2 + tower_taper_height + tower_straight_height / 2)
        )
        parts.append(straight_part_component)

    # --- Perform a Single Union Operation on All Parts ---
    # FIX: Use gf.union for merging a list of components, not gf.boolean.
    # gf.boolean requires two arguments, A and B. gf.union is designed for
    # merging a list of components.
    final_device = gf.union(parts, layer=layer)
    
    return final_device

# Main execution block to generate, save, and show the GDS
if __name__ == "__main__":
    device = create_device()
    
    # Explicitly write the GDS file to disk.
    device.write_gds("output.gds")
    
    # Show the layout in KLayout viewer
    device.show()

    print("GDS file 'output.gds' has been generated successfully.")