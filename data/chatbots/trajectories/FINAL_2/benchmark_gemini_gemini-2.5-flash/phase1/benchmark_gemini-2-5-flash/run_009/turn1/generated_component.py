import gdsfactory as gf

@gf.cell
def bottle(height_total: float, top_rect_height_ratio: float, top_rect_width: float, taper_base_width: float, layer=(1, 0)) -> gf.Component:
    """
    Creates a single 'bottle' shaped pillar with a rectangular top and a tapered base.

    Args:
        height_total: Total height of the bottle.
        top_rect_height_ratio: Ratio of the total height for the top rectangular part.
        top_rect_width: Width of the top rectangular part.
        taper_base_width: Width of the tapered base where it connects to the main body.
        layer: GDS layer for the geometry.

    Returns:
        A GDSFactory Component representing one bottle.
    """
    c = gf.Component("bottle")
    
    # Calculate heights for rectangular and tapered parts
    top_rect_h = height_total * top_rect_height_ratio
    taper_h = height_total - top_rect_h

    # Create the top rectangular part
    # `centered=True` places its local origin at its center.
    rect_top = gf.components.rectangle(size=(top_rect_width, top_rect_h), centered=True, layer=layer)
    
    # Create the tapered part (trapezoid) using path extrusion with a transition
    # The path defines the extrusion direction (from y=0 to y=taper_h).
    p_taper_path = gf.path.straight(length=taper_h)
    
    # Define two fixed-width cross-sections for the start and end of the taper
    # The start of the taper (bottom) has width = taper_base_width
    xs_taper_start = gf.cross_section.cross_section(width=taper_base_width, layer=layer)
    # The end of the taper (top) has width = top_rect_width
    xs_taper_end = gf.cross_section.cross_section(width=top_rect_width, layer=layer)
    
    # Create a transition object between the two cross-sections
    # The default `width_type='linear'` is suitable for a simple taper.
    taper_transition = gf.path.transition(xs_taper_start, xs_taper_end)
    
    # Extrude the path using the transition
    taper_comp = gf.path.extrude_transition(p_taper_path, taper_transition)

    # Add and position the components within the `bottle` cell
    # The `taper_comp` is created with its bottom-center at (0,0) locally.
    taper_ref = c << taper_comp
    
    # Position the top rectangle. Its bottom edge should align with the top edge of the taper.
    # Since `rect_top` is `centered=True`, its center is at its local origin (0,0).
    # We move its center to `y = (top_of_taper_y) + (half_height_of_rect)`.
    rect_top_ref = c << rect_top
    rect_top_ref.movey(taper_h + top_rect_h / 2)
    
    # The resulting `c` component (the bottle) will have its base at y=0 and be horizontally centered at x=0.
    return c

@gf.cell
def my_device() -> gf.Component:
    """
    Recreates the device geometry from the PNG image using GDSFactory parametric functions.
    The device has a footprint of 25x10 µm.

    Returns:
        A GDSFactory Component representing the complete device.
    """
    c = gf.Component("my_device")
    layer = (1, 0)

    # --- Global Dimensions ---
    total_width = 25.0
    total_height = 10.0

    # List to hold all sub-components before boolean combining
    components_to_combine = []

    # 1. Bottom Feature (inverted trapezoid)
    # This feature defines the lowest point (y=0) and connects to the main body at y=2.
    h_bottom_feat = 2.0
    w_bottom_feat_base = 2.0  # Width at y=0
    w_bottom_feat_top = 5.0   # Width at y=h_bottom_feat (connects to main body)
    
    # Create path for the bottom feature (path goes from y=0 to y=h_bottom_feat)
    p_bottom_feat = gf.path.straight(length=h_bottom_feat)
    
    # Define two fixed-width cross-sections for the start and end of the bottom feature
    xs_bottom_start = gf.cross_section.cross_section(width=w_bottom_feat_base, layer=layer)
    xs_bottom_end = gf.cross_section.cross_section(width=w_bottom_feat_top, layer=layer)
    
    # Create a transition object
    bottom_feat_transition = gf.path.transition(xs_bottom_start, xs_bottom_end)
    
    # Extrude the path using the transition
    bottom_feat_comp = gf.path.extrude_transition(p_bottom_feat, bottom_feat_transition)
    
    # Position the component: its bottom-center (0,0) should be at (total_width/2, 0).
    bottom_feat_comp.movex(total_width / 2) 
    components_to_combine.append(bottom_feat_comp)

    # 2. Main Body (solid rectangle)
    # This rectangle sits on top of the bottom feature, spanning the full width.
    # It starts at y = h_bottom_feat (2.0) and extends upwards.
    h_main_rect_height = 5.0 # Height of the main rectangular part.
    # So, its top edge will be at y = 2.0 + 5.0 = 7.0.
    
    # Create the rectangle. `centered=False` means its bottom-left is at (0,0) locally.
    main_rect_comp = gf.components.rectangle(size=(total_width, h_main_rect_height), centered=False, layer=layer)
    # Position its bottom edge at h_bottom_feat.
    main_rect_comp.movey(h_bottom_feat) 
    components_to_combine.append(main_rect_comp)

    # 3. Top Pillars (Bottles)
    # These sit on top of the main body, from y=7.0 to y=10.0.
    pillar_height = total_height - (h_bottom_feat + h_main_rect_height) # 10 - 7 = 3.0 µm
    
    # Parameters for the `bottle` component
    pillar_top_rect_h_ratio = 0.5 # Top rect is 1.5 µm tall
    pillar_top_rect_width = 2.0   # Top rect is 2.0 µm wide
    pillar_taper_base_width = 3.0 # Taper base is 3.0 µm wide

    num_pillars = 4
    
    # Calculate spacing between pillars:
    # Total width (25) = (2 * exterior_gap) + (3 * interior_gap) + (4 * pillar_taper_base_width)
    # Assuming exterior_gap = interior_gap (let's call it `gap_unit`):
    # 5 * `gap_unit` + 4 * 3.0 = 25.0
    # 5 * `gap_unit` + 12.0 = 25.0
    # 5 * `gap_unit` = 13.0
    gap_unit = 13.0 / 5.0  # = 2.6 µm
    
    # Starting x-coordinate for the center of the first pillar.
    # It's `exterior_gap` from the left edge + half of its base width.
    x_current_pillar_center = gap_unit + (pillar_taper_base_width / 2)
    
    # Base y-coordinate for the pillars.
    pillar_base_y = h_bottom_feat + h_main_rect_height # = 2.0 + 5.0 = 7.0 µm
    
    for i in range(num_pillars):
        single_bottle_comp = bottle(
            height_total=pillar_height,
            top_rect_height_ratio=pillar_top_rect_h_ratio,
            top_rect_width=pillar_top_rect_width,
            taper_base_width=pillar_taper_base_width,
            layer=layer
        )
        # Position the bottle component. Its local origin is its bottom-center.
        single_bottle_comp.move((x_current_pillar_center, pillar_base_y))
        components_to_combine.append(single_bottle_comp)
        
        # Increment x_current for the next pillar.
        # Move by (`pillar_taper_base_width` + `interior_gap`).
        x_current_pillar_center += pillar_taper_base_width + gap_unit
    
    # --- Boolean Combination ---
    # Perform boolean OR operation to combine all shapes into a single component.
    if not components_to_combine:
        raise ValueError("No components were created to combine.")
    
    # Start with a copy of the first component. This ensures the original component
    # in the list is not locked by the first boolean operation.
    final_combined_shape = components_to_combine[0].copy()

    for i in range(1, len(components_to_combine)):
        # Pass a copy of the next component to combine.
        # This prevents the `Cell locked` error as each boolean operation
        # works on a fresh, unlocked copy of the component from the list.
        final_combined_shape = gf.boolean(
            final_combined_shape,
            components_to_combine[i].copy(), # Pass a copy
            operation="or",
            layer=layer
        )
    
    # Add the final combined shape to the main device component.
    c << final_combined_shape
    
    return c

# --- Generate and Verify the Device ---
if __name__ == "__main__":
    device = my_device()
    device.write_gds("my_device.gds")

    # Verify the footprint of the created device
    # GDSFactory's .size property provides (width, height) of the bounding box
    actual_width, actual_height = device.size
    
    expected_width = 25.0
    expected_height = 10.0

    print(f"Generated device size: Width = {actual_width:.2f} µm, Height = {actual_height:.2f} µm")

    # Assertions to ensure the footprint matches the requirements
    assert abs(actual_width - expected_width) < 1e-6, f"Width mismatch: Expected {expected_width}, got {actual_width}"
    assert abs(actual_height - expected_height) < 1e-6, f"Height mismatch: Expected {expected_height}, got {actual_height}"

    print("Device generated successfully and footprint verified.")
    # To visualize the GDS, you can open 'my_device.gds' in a GDS viewer or use GDSFactory's plot function:
    # gf.show(device) # Uncomment to show the device in a pop-up window