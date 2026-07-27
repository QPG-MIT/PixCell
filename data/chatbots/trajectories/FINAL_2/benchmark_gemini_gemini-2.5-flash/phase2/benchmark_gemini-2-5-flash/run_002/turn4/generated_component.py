import gdsfactory as gf
import numpy as np

@gf.cell
def my_device():
    """
    Recreates the geometry from the provided image using GDSFactory parametric functions.

    The device consists of a main rectangular body with a V-shaped notch at the bottom,
    and four tapered pillars (towers) on top.

    The entire geometry is designed to fit within a 25um x 10um footprint.
    """
    c = gf.Component("my_device")
    layer = (1, 0) # Default layer for all geometry

    # Device footprint constraint (total width and height)
    total_width = 25.0
    total_height = 10.0

    # Small overlap epsilon to ensure boolean operations merge/cut correctly.
    overlap_epsilon = 0.001 # A small value, e.g., 1 nanometer

    # --- Dimension Breakdown (adjusted to fit 25x10um footprint based on visual comparison) ---
    # We define the total height (10um) as spanning from the lowest point of the notch
    # to the highest point of the towers, centered around Y=0.

    # Vertical Coordinates and Heights (relative to Y=0 center)
    Y_min_overall = -total_height / 2.0 # = -5.0 (lowest point of the notch)
    Y_max_overall = total_height / 2.0  # = 5.0 (highest point of the towers)

    # 1. Main Body and Notch Dimensions
    # Y_main_body_top: The top edge of the main rectangular body, where towers start.
    # From visual, this should be quite low in the overall height.
    Y_main_body_top = 1.0 # Adjusted to make main body shorter, towers taller

    # main_body_rect_height: Height of the solid rectangular part of the main body.
    # This is the height from Y_main_body_bottom to Y_main_body_top.
    main_body_rect_height = 3.5 # Adjusted

    # Y_main_body_bottom: The bottom edge of the main rectangular body, where the notch starts.
    Y_main_body_bottom = Y_main_body_top - main_body_rect_height # = 1.0 - 3.5 = -2.5

    # notch_height: Depth of the V-shaped notch.
    # The notch tip needs to be at Y_min_overall.
    notch_height = Y_main_body_bottom - Y_min_overall # = -2.5 - (-5.0) = 2.5 # Adjusted

    # notch_top_width: Width of the notch at its top edge (at Y_main_body_bottom).
    notch_top_width = 8.0 # Adjusted for a wider notch

    main_body_rect_width = total_width # Main body spans the full width

    # 2. Tower (Pillars on top of the main body) Dimensions
    # tower_total_height: Total height of the towers, from Y_main_body_top to Y_max_overall.
    tower_total_height = Y_max_overall - Y_main_body_top # = 5.0 - 1.0 = 4.0 # Adjusted

    # Breakdown tower height into top rectangular part and tapered part
    tower_top_height = 0.5  # Adjusted for a much shorter rectangular top part
    tower_taper_height = tower_total_height - tower_top_height # = 4.0 - 0.5 = 3.5 # Adjusted

    # Tower widths
    tower_bottom_width = 3.0 # Adjusted for a narrower base
    tower_top_width = 1.5   # Adjusted for a narrower top

    # --- Constructing the Geometry ---

    # 1. Create Main Body Rectangle Component (positioned)
    base_rect_component = gf.components.rectangle(
        size=(main_body_rect_width, main_body_rect_height), layer=layer, centered=True
    )
    main_rect_positioned = base_rect_component.copy()
    # Move the main rectangle so its bottom (ymin) is at Y_main_body_bottom.
    main_rect_positioned.movey(Y_main_body_bottom - main_rect_positioned.ymin)


    # 2. Create Notch Triangle Component (positioned and rotated for subtraction)
    # gf.components.triangle(x, y) creates an isosceles triangle with base (x) on the x-axis,
    # centered at x/2, and tip at (x/2, y).
    base_notch_triangle_component = gf.components.triangle(x=notch_top_width, y=notch_height, layer=layer)
    notch_triangle_transformed = base_notch_triangle_component.copy()
    notch_triangle_transformed.rotate(180) # Now it points downwards (tip at y=-notch_height, base at y=0 in local coords)
    # Position the notch triangle. Its local y=0 (which is its base after rotation) needs to slightly
    # overlap the bottom of the main rectangle (Y_main_body_bottom) for the boolean subtraction to work.
    notch_triangle_transformed.movey(Y_main_body_bottom + overlap_epsilon - notch_triangle_transformed.ymax)

    # Perform boolean subtraction to create the main body with the notch.
    main_body_with_notch = gf.boolean(main_rect_positioned, notch_triangle_transformed, operation="not", layer=layer)


    # 3. Define a Reusable Single Tower Component
    @gf.cell
    def _single_tower_component(top_width, top_height, taper_height, bottom_width, layer):
        """Creates a single tower (pillar) component.
        Its local origin (0,0) will be at the bottom-center of its wider base."""
        tower_comp = gf.Component("single_tower_sub")

        # Top rectangular part of the tower
        rect_part_base = gf.components.rectangle(size=(top_width, top_height), layer=layer, centered=True)
        rect_ref = tower_comp << rect_part_base

        # Tapered (trapezoidal) part of the tower
        # Taper is created horizontally, from width1 to width2 along length.
        taper_horizontal_base = gf.components.taper(
            length=taper_height, width1=bottom_width, width2=top_width, layer=layer
        )
        taper_ref = tower_comp << taper_horizontal_base
        taper_ref.rotate(90) # Rotates around (0,0). After rotation, its ymin is 0, ymax is taper_height, and x is centered at 0.

        # Position the rectangle part on top of the taper part.
        rect_ref.x = taper_ref.x # Align centers horizontally (both are 0 relative to tower_comp)
        rect_ref.ymin = taper_ref.ymax # Align bottom of rect to top of taper

        return tower_comp

    single_tower_comp_template = _single_tower_component(
        top_width=tower_top_width,
        top_height=tower_top_height,
        taper_height=tower_taper_height,
        bottom_width=tower_bottom_width,
        layer=layer
    )

    # 4. Create and Position the Four Towers
    num_towers = 4

    # Horizontal distribution for towers: define the total span they occupy
    towers_total_span = 20.0 # Total width from left edge of first tower to right edge of last tower
    x_leftmost_tower_edge = -towers_total_span / 2.0 # For 25um total_width, this allows 2.5um outer gaps
    x_rightmost_tower_edge = towers_total_span / 2.0

    # Calculate center-to-center spacing for even distribution
    x_center_first_tower = x_leftmost_tower_edge + tower_bottom_width / 2.0
    x_center_last_tower = x_rightmost_tower_edge - tower_bottom_width / 2.0
    total_center_span = x_center_last_tower - x_center_first_tower
    center_to_center_spacing = total_center_span / (num_towers - 1) # (num_towers - 1) internal gaps

    tower_x_centers = []
    current_x_center = x_center_first_tower
    for _ in range(num_towers):
        tower_x_centers.append(current_x_center)
        current_x_center += center_to_center_spacing


    positioned_tower_components = []
    for x_center in tower_x_centers:
        tower_instance = single_tower_comp_template.copy()
        tower_instance.x = x_center
        # Position the tower so its bottom (ymin=0 in _single_tower_component's local system)
        # is slightly *below* Y_main_body_top to ensure overlap for the boolean union.
        tower_instance.movey(Y_main_body_top - overlap_epsilon)
        positioned_tower_components.append(tower_instance)

    # 5. Union all components into a single GDS shape
    # Collect all top-level components that need to be unioned.
    components_to_union = [main_body_with_notch] + positioned_tower_components

    # Create a temporary component to hold all these, just for the boolean operation.
    temp_container_for_final_union = gf.Component("temp_container_for_final_union")
    for comp_to_add in components_to_union:
        temp_container_for_final_union << comp_to_add

    # Perform a self-boolean "or" operation on the temporary container to union all parts.
    final_merged_geometry = gf.boolean(
        temp_container_for_final_union, temp_container_for_final_union, operation="or", layer=layer
    )

    # Add only the final merged geometry as a reference to the main component `c`.
    c << final_merged_geometry

    return c

if __name__ == "__main__":
    device = my_device()
    device.write_gds("my_device.gds")
    # device.show() # Uncomment to visualize with KLayout if installed