import gdsfactory as gf

@gf.cell
def create_device() -> gf.Component:
    """
    Recreates the specified geometry using GDSFactory parametric functions
    within a 25um x 10um footprint.
    """
    c = gf.Component("my_gdsfactory_device")

    # 1. Define common parameters
    W_total = 25  # Total device width
    H_total = 10  # Total device height
    LAYER = (1, 0) # GDSII layer and datatype
    xs = gf.cross_section.cross_section(layer=LAYER) # Generic cross-section for tapers

    # 2. Define dimensions for main components
    H_body = 6  # Height of the main rectangular body
    W_body = W_total # Main body spans full width

    H_notch = 1 # Height of the V-shaped notch
    W_notch_top = 5 # Top width of the V-notch
    W_notch_bottom = 1 # Bottom width of the V-notch

    H_spire_taper = 2 # Height of the tapered part of a spire
    W_spire_base_bottom = 2.5 # Bottom width of the spire's tapered part (where it meets main body)
    W_spire_base_top = 1.0 # Top width of the spire's tapered part (where it meets rectangular top)

    H_spire_rect = 1 # Height of the rectangular part of a spire
    W_spire_rect = W_spire_base_top # Width of the spire's rectangular part

    # ADDED BACK: Horizontal gaps for spire positioning
    gap_outer = 3 # Horizontal gap from device edge to first/last spire base
    gap_inner = 3 # Horizontal gap between spire bases

    # --- 3. Create the main body (rectangle) ---
    # Centered at (0,0), so it spans from x [-12.5, 12.5] and y [-3, 3]
    main_body_rect = gf.components.rectangle(size=(W_body, H_body), centered=True, layer=LAYER)

    # --- 4. Create the V-shaped notch (taper component) ---
    # The taper component by default has its `width1` end at (0,0) and extends along +X.
    notch_taper_comp = gf.components.taper(
        length=H_notch,
        width1=W_notch_top,  # This will be the top width of the V
        width2=W_notch_bottom, # This will be the bottom width of the V
        cross_section=xs
    )
    # Create a temporary Component for the notch with correct rotation and position
    notch_comp_rotated_moved = gf.Component("notch_rotated_moved")
    notch_ref_temp = notch_comp_rotated_moved << notch_taper_comp
    notch_ref_temp.rotate(-90) # Rotate -90 degrees (clockwise).
                               # Now, its `width1` (W_notch_top) is centered on x=0 at y=0,
                               # and the taper extends downwards along -Y to y=-H_notch.
                               # So, the top edge of the notch is at y=0 in its local coordinate system.

    # Position the notch: its top edge (at y=0 in its local coord system)
    # should align with the bottom of the main_body_rect (-H_body/2).
    notch_ref_temp.movey(-H_body/2)
    # The taper is horizontally centered by default (width1 centered on x=0), which is correct for subtraction from a centered rectangle.

    # --- 5. Perform boolean operation to cut the notch from the main body ---
    body_with_notch = gf.boolean(main_body_rect, notch_comp_rotated_moved, operation="not", layer=LAYER)

    # --- 6. Create a single spire template (Component) ---
    spire_cell = gf.Component("single_spire_template")

    # Tapered base part of the spire
    # Taper is created with `width1` at (0,0) and extends along +X.
    spire_taper_comp = gf.components.taper(
        length=H_spire_taper,
        width1=W_spire_base_bottom, # This will be the bottom width of the spire taper
        width2=W_spire_base_top,    # This will be the top width of the spire taper
        cross_section=xs
    )
    st_ref = spire_cell << spire_taper_comp
    st_ref.rotate(90) # Rotate +90 degrees (counter-clockwise).
                      # Now, its `width1` (W_spire_base_bottom) is centered on x=0 at y=0,
                      # and the taper extends upwards along +Y to y=H_spire_taper.
                      # So, the bottom edge of the taper is at y=0 in its local coordinate system.
    # No vertical movement needed for st_ref, as its bottom is already at y=0 inside spire_cell.

    # Rectangular top part of the spire
    spire_rect_comp = gf.components.rectangle(size=(W_spire_rect, H_spire_rect), centered=True, layer=LAYER)
    sr_ref = spire_cell << spire_rect_comp
    # Position the rectangle on top of the taper:
    # The taper's top edge is at y = H_spire_taper (in spire_cell's coordinates).
    # The rectangle's bottom edge (relative to its own centered origin) is at -H_spire_rect/2.
    # So, move the rectangle's center up by (H_spire_taper + H_spire_rect/2)
    sr_ref.movey(H_spire_taper + H_spire_rect/2)
    # At this point, `spire_cell` is centered horizontally at x=0, and its bottom edge is at y=0.

    # --- 7. Position and prepare the four spire instances ---
    x_positions = []
    # Calculate the starting x-position for the center of the first spire's base.
    # Left edge of W_body is -W_body/2.
    # The spire's `width1` (W_spire_base_bottom) is centered at its local x=0.
    start_x = -W_body / 2 + gap_outer + W_spire_base_bottom / 2
    spire_x_step = W_spire_base_bottom + gap_inner

    for i in range(4):
        x_positions.append(start_x + i * spire_x_step)

    # Y-position for the bottom edge of each spire.
    # This aligns with the top of the main body, which is at H_body/2 (relative to its center at 0,0).
    y_position_spires = H_body / 2

    # Collect all components (body + 4 spires) for the final union operation
    all_shapes_to_union = [body_with_notch] # Start with the main body with its notch

    for x_pos in x_positions:
        # Create a new temporary Component for each spire instance with correct placement
        placed_spire = gf.Component(f"placed_spire_{x_pos}") # Naming helps with debugging
        spire_ref_instance = placed_spire << spire_cell # Add an instance of the template
        # Move the spire instance: its bottom-center (at (0,0) of spire_cell)
        # to the calculated (x_pos, y_position_spires).
        spire_ref_instance.move((x_pos, y_position_spires))
        all_shapes_to_union.append(placed_spire)

    # --- 8. Perform a single union (OR) operation on all collected shapes ---
    # gf.boolean returns a new Component, which will be appropriately centered
    # based on the union of all input shapes.
    final_device_geom = gf.boolean(all_shapes_to_union, operation="or", layer=LAYER)

    # --- 9. Add the final result to the main component `c` ---
    c.add_ref(final_device_geom)

    # Verification: Print the bounding box and dimensions to ensure it matches the footprint.
    bbox = c.bbox
    width = bbox[1][0] - bbox[0][0]
    height = bbox[1][1] - bbox[0][1]
    print(f"Final device bounding box: {bbox}")
    print(f"Actual device width: {width:.2f} um")
    print(f"Actual device height: {height:.2f} um")
    
    # Expected: width=25.00um, height=10.00um
    # Expected BBox: [[-12.5, -5.0], [12.5, 5.0]]
    assert abs(width - W_total) < 1e-6, f"Width mismatch: {width} vs {W_total}"
    assert abs(height - H_total) < 1e-6, f"Height mismatch: {height} vs {H_total}"

    return c

# Create and save the device when the script is executed
if __name__ == "__main__":
    device = create_device()
    device.write_gds("my_gdsfactory_device.gds")
    # To visualize in KLayout (if installed and configured)
    # device.show()