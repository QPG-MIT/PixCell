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

    # --- Dimension Breakdown (adjusted to fit 25x10um footprint) ---
    # We define the total height (10um) as spanning from the lowest point of the notch
    # to the highest point of the towers.
    # Visually estimating proportions from the image:
    # H_towers (pillars) ~ 3.5um
    # H_notch (V-cut) ~ 1.5um
    # H_main_body_rectangle (the core rectangular part) = H_total - H_towers - H_notch
    # H_main_body_rectangle = 10.0 - 3.5 - 1.5 = 5.0um

    # Main Body Rectangle Dimensions (the central rectangular block, excluding notch and towers)
    main_body_rect_height = 5.0
    main_body_rect_width = total_width

    # Notch Dimensions (V-shape cut at the bottom of the main body)
    notch_height = 1.5
    notch_top_width = 3.0 # The width of the V-cut at its top (where it meets the main body)

    # Tower (Pillars on top of the main body) Dimensions
    tower_top_height = 1.5
    tower_taper_height = 2.0
    tower_top_width = 1.5
    tower_bottom_width = 2.5 # Width of the tower at its base (where it meets the main body)
    tower_total_height = tower_top_height + tower_taper_height # Sums to 3.5um

    # --- Positioning Calculation for Centering (entire device within [-12.5, 12.5] x [-5, 5]) ---
    # Lowest Y-coordinate of the device (bottom of the notch)
    Y_notch_bottom = -total_height / 2.0 # = -5.0
    # Y-coordinate where the main body rectangle begins (top of the notch, or bottom of main rect)
    Y_main_body_bottom = Y_notch_bottom + notch_height # = -5.0 + 1.5 = -3.5
    # Y-coordinate where the main body rectangle ends (top of the main rect, or bottom of towers)
    Y_main_body_top = Y_main_body_bottom + main_body_rect_height # = -3.5 + 5.0 = 1.5
    # Y-coordinate where the towers end (top of the device)
    Y_towers_top = Y_main_body_top + tower_total_height # = 1.5 + 3.5 = 5.0


    # 1. Create Main Body Rectangle Component (positioned)
    # Get the base rectangle component (centered at 0,0).
    base_rect_component = gf.components.rectangle(
        size=(main_body_rect_width, main_body_rect_height), layer=layer, centered=True
    )
    # Create a *copy* of this component, then move the copy.
    # This ensures we are modifying an unlocked, independent component.
    main_rect_positioned = base_rect_component.copy()
    main_rect_positioned.movey(Y_main_body_bottom - main_rect_positioned.ymin)


    # 2. Create Notch Triangle Component (positioned and rotated)
    # Get the base triangle component (base centered at 0,0, vertex at (0, y)).
    base_notch_triangle_component = gf.components.triangle(x=notch_top_width, y=notch_height, layer=layer)
    # Create a *copy* for transformations.
    notch_triangle_transformed = base_notch_triangle_component.copy()
    # Rotate 180 degrees.
    # After rotation, its base is still centered on the x-axis (y=0), but it points downwards.
    # Its ymin will be -notch_height, ymax will be 0.
    notch_triangle_transformed.rotate(180)
    # Position the notch triangle so its base (ymax after rotation) aligns with Y_main_body_bottom.
    notch_triangle_transformed.movey(Y_main_body_bottom - notch_triangle_transformed.ymax)


    # Perform boolean subtraction to create the main body with the notch.
    # These are independent, moved components, so `gf.boolean` should work without lock errors.
    main_body_with_notch = gf.boolean(main_rect_positioned, notch_triangle_transformed, operation="not", layer=layer)


    # 3. Define a Reusable Single Tower Component
    @gf.cell
    def _single_tower_component(top_width, top_height, taper_height, bottom_width, layer):
        """Creates a single tower (pillar) component."""
        tower_comp = gf.Component("single_tower_sub")

        # Top rectangular part of the tower
        rect_part = gf.components.rectangle(size=(top_width, top_height), layer=layer, centered=True)
        # Add as a reference to the sub-component and then move the reference. This is the correct internal pattern.
        rect_ref = tower_comp << rect_part

        # Tapered (trapezoidal) part of the tower
        taper_horizontal = gf.components.taper(
            length=taper_height, width1=bottom_width, width2=top_width, layer=layer
        )
        taper_ref = tower_comp << taper_horizontal
        # Rotate the reference.
        taper_ref.rotate(90) # Rotates around (0,0). The wider base is now centered on X-axis at Y=0.

        # Position the rectangle part on top of the taper part by moving its reference.
        # `rect_ref` is centered at (0,0) within `tower_comp`. Its `ymin` is `-top_height/2`.
        # `taper_ref`'s top (narrower part) is centered on X-axis at `Y=taper_height` within `tower_comp`.
        # We set `rect_ref`'s center `x` to `taper_ref`'s `x` (which is 0) and its `ymin` to `taper_ref`'s `ymax`.
        rect_ref.center = (taper_ref.x, taper_ref.ymax + top_height / 2.0)

        # The `tower_comp`'s origin (0,0) will be at the bottom-center of its wider base.
        return tower_comp

    single_tower_comp = _single_tower_component(
        top_width=tower_top_width,
        top_height=tower_top_height,
        taper_height=tower_taper_height,
        bottom_width=tower_bottom_width,
        layer=layer
    )

    # 4. Create and Position the Four Towers
    num_towers = 4

    # Calculate horizontal spacing
    gap_width = (total_width - (num_towers * tower_bottom_width)) / (num_towers + 1)

    tower_x_centers = []
    current_x = -total_width / 2.0 + gap_width + (tower_bottom_width / 2.0)
    for _ in range(num_towers):
        tower_x_centers.append(current_x)
        current_x += (tower_bottom_width + gap_width)

    positioned_tower_components = []
    for x_center in tower_x_centers:
        # Create a *copy* of the single_tower_comp for each placement.
        # This `tower_instance` is a new, independent component that can be moved.
        tower_instance = single_tower_comp.copy()
        tower_instance.x = x_center
        tower_instance.movey(Y_main_body_top)
        positioned_tower_components.append(tower_instance)

    # 5. Union all components into a single GDS shape
    # Collect all top-level components that need to be unioned.
    # These are all independent `gf.Component` objects.
    components_to_union = [main_body_with_notch] + positioned_tower_components

    # Create a temporary component to hold all these, just for the boolean operation.
    temp_container_for_final_union = gf.Component("temp_container_for_final_union")
    for comp_to_add in components_to_union:
        # Add references to the temporary container. gf.boolean will flatten these.
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