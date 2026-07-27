import gdsfactory as gf

@gf.cell
def create_bar_with_tapers(
    central_feature_length: float,
    bar_width: float,
    hole_width: float,
    hole_length: float,
    hole_spacing_x: float,
    taper_length: float,
    taper_final_width: float,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Creates one horizontal bar structure with a central segment containing
    two rectangular holes, and two tapered segments on its ends.

    Args:
        central_feature_length: Length of the main central rectangular part.
        bar_width: Width of the main horizontal bar segment.
        hole_width: Width of the rectangular holes.
        hole_length: Length of the rectangular holes.
        hole_spacing_x: Horizontal distance between the centers of the two holes.
        taper_length: Length of each tapered segment.
        taper_final_width: Width of the taper at its wider end (connecting outwards).
        layer: GDS layer for the geometry.

    Returns:
        A gdsfactory Component representing one complete horizontal bar structure.
    """
    bar_c = gf.Component()

    # 1. Central segment with holes
    # Create the base rectangle for the central part
    base_rect = gf.components.rectangle(
        size=(central_feature_length, bar_width), layer=layer, centered=True
    )

    # Create the rectangular "hole" primitive - it is centered at (0,0)
    hole_primitive = gf.components.rectangle(
        size=(hole_length, hole_width), layer=layer, centered=True
    )

    # Add base_rect as a reference
    ref_base_rect = bar_c << base_rect
    
    # Add hole primitives as references, then move the references
    ref_hole1 = bar_c << hole_primitive
    ref_hole2 = bar_c << hole_primitive # Use the same primitive for the second hole

    # Position hole references relative to the center of the base rectangle
    hole_x_offset_from_center = hole_spacing_x / 2 + hole_length / 2
    ref_hole1.movex(-hole_x_offset_from_center)  # Move the REFERENCE, not the primitive Component
    ref_hole2.movex(hole_x_offset_from_center)   # Move the REFERENCE

    # Perform first boolean "not" operation
    # `temp_central_geom_1` is a new Component from the boolean operation.
    temp_central_geom_1 = gf.boolean(ref_base_rect, ref_hole1, operation="not", layer=layer)
    # Add this intermediate result as a reference. This is crucial for chaining booleans safely.
    ref_temp_central_1 = bar_c << temp_central_geom_1

    # Perform second boolean "not" operation using the *reference* to the previous result
    central_part_final_geom = gf.boolean(ref_temp_central_1, ref_hole2, operation="not", layer=layer)
    # Add the final central part as a reference
    central_part_ref = bar_c << central_part_final_geom

    # 2. Tapered segments
    taper_left_primitive = gf.components.taper(
        length=taper_length, width1=taper_final_width, width2=bar_width, layer=layer
    )
    taper_right_primitive = gf.components.taper(
        length=taper_length, width1=bar_width, width2=taper_final_width, layer=layer
    )

    # Add tapers as references
    ref_taper_left = bar_c << taper_left_primitive
    ref_taper_right = bar_c << taper_right_primitive

    # Position tapers
    ref_taper_left.movex(-central_feature_length / 2 - taper_length)
    ref_taper_right.movex(central_feature_length / 2)

    # 3. Merge all components into a single geometry for the full horizontal bar
    # Collect all relevant ComponentReferences and perform a single boolean "or" operation.
    all_parts_to_merge_refs = [central_part_ref, ref_taper_left, ref_taper_right]
    full_bar_final_geom = gf.boolean(all_parts_to_merge_refs, operation="or", layer=layer)
    
    # Add the final merged geometry to the component as the single main body
    bar_c.add_ref(full_bar_final_geom) 

    # Clean up all intermediate references from the component
    bar_c.remove(ref_base_rect)
    bar_c.remove(ref_hole1)
    bar_c.remove(ref_hole2)
    bar_c.remove(ref_temp_central_1) 
    bar_c.remove(central_part_ref)   
    bar_c.remove(ref_taper_left)
    bar_c.remove(ref_taper_right)
    
    return bar_c

@gf.cell
def my_device() -> gf.Component:
    """
    Creates the complete device geometry as shown in the image,
    adhering to the specified footprint.
    """
    c = gf.Component("oval_device")
    layer = (1, 0) # Default GDS layer

    # --- Footprint and Overall Dimensions (from constraint) ---
    x_total = 3.0  # Total width of the device
    y_total = 5.5  # Total height of the device

    x_radius_outer = x_total / 2  # X-radius for the outer ellipse
    y_radius_outer = y_total / 2  # Y-radius for the outer ellipse

    # --- 1. Outer Oval Frame ---
    border_thickness = 0.15 # Thickness of the elliptical frame
    outer_ellipse = gf.components.ellipse(radii=(x_radius_outer, y_radius_outer), layer=layer)
    inner_ellipse = gf.components.ellipse(
        radii=(x_radius_outer - border_thickness, y_radius_outer - border_thickness), layer=layer
    )
    
    # Use boolean "not" to create the hollow frame
    oval_frame_geom = gf.boolean(outer_ellipse, inner_ellipse, operation="not", layer=layer)
    c.add_ref(oval_frame_geom) # Add the resulting frame to the main component

    # --- 2. Parameters for Internal Horizontal Structures ---
    bar_width = 0.2          # Width of the main horizontal bar segment
    bar_separation_y = 1.5   # Vertical distance between the centers of the two horizontal structures
    y_offset_bar = bar_separation_y / 2 # Y-offset for the top bar (positive), bottom bar (negative)

    central_feature_length = 1.0 # Length of the central part that has holes
    hole_width = 0.15            # Width of the rectangular holes
    hole_length = 0.2            # Length of the rectangular holes
    hole_spacing_x = 0.1         # Distance between the inner edges of the holes (center-to-center for holes)
    taper_length = 0.4           # Length of the tapers
    taper_final_width = 0.3      # Width of the taper where it meets the oval frame

    # Create the top horizontal structure using the helper function
    top_bar_ref = c << create_bar_with_tapers(
        central_feature_length, bar_width, hole_width, hole_length, hole_spacing_x,
        taper_length, taper_final_width, layer
    )
    top_bar_ref.movey(y_offset_bar) # Position it above the center

    # Create the bottom horizontal structure by instantiating another and moving it
    bottom_bar_ref = c << create_bar_with_tapers(
        central_feature_length, bar_width, hole_width, hole_length, hole_spacing_x,
        taper_length, taper_final_width, layer
    )
    bottom_bar_ref.movey(-y_offset_bar) # Position it below the center

    return c

# Example usage and GDS output (for local testing/verification)
if __name__ == "__main__":
    device = my_device()
    
    # Output GDS file (optional)
    # device.write_gds("oval_device_recreated.gds")

    # Display the component (requires KLayout or similar viewer configured with gdsfactory)
    device.show()

    # Verify footprint programmatically
    bounds = device.bounds
    width_actual = bounds[1][0] - bounds[0][0]
    height_actual = bounds[1][1] - bounds[0][1]
    print(f"Device width (actual): {width_actual:.2f} um")
    print(f"Device height (actual): {height_actual:.2f} um")
    print(f"Expected width: {3.0} um, Expected height: {5.5} um")

    # Assertions for automated checks (optional)
    assert abs(width_actual - 3.0) < 1e-3, f"X-footprint mismatch: {width_actual} != 3.0"
    assert abs(height_actual - 5.5) < 1e-3, f"Y-footprint mismatch: {height_actual} != 5.5"