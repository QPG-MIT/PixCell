import gdsfactory as gf

@gf.cell
def custom_device() -> gf.Component:
    """
    Recreates the device geometry shown in the image using GDSFactory
    parametric functions and boolean operations.
    """
    c = gf.Component("custom_device")
    layer = (1, 0) # Default layer for all geometry

    # --- 1. Define device dimensions and sub-component parameters ---
    # Overall device footprint as specified in the problem
    device_width = 25.0
    device_height = 10.0

    # Dimensions for the main rectangular block
    main_block_width = device_width
    main_block_height = 7.0 

    # Dimensions for the trapezoidal notch at the bottom center
    notch_bottom_width = 2.5  # Adjusted: Slightly wider bottom for the notch
    notch_top_width = 1.0     # Narrower flat top of the notch
    notch_height = 1.5        # Height of the notch

    # Dimensions for each of the four towers (Adjusted for better visual match)
    tower_cap_width = 1.0       # Narrower rectangular cap at the very top
    tower_cap_height = 0.5      # Height of the rectangular cap
    
    tower_taper_top_width = 2.0 # Width at the top of the trapezoidal section (wider than cap)
    tower_taper_base_width = 4.0 # The widest part of the tower's base (where it meets the main block)
    tower_taper_height = device_height - main_block_height - tower_cap_height # Calculated: 10.0 - 7.0 - 0.5 = 2.5

    # --- 2. Create the main block (rectangle with a trapezoidal notch subtracted) ---
    # 2.1. Create the initial large rectangular base.
    # `centered=False` places its bottom-left corner at (0,0).
    main_rect_c = gf.components.rectangle(
        size=(main_block_width, main_block_height), layer=layer, centered=False
    )
    
    # 2.2. Create the trapezoidal notch component by adding a polygon to a new Component.
    notch_c = gf.Component("notch_shape") 
    # Vertices for a trapezoid centered horizontally at x=0, with bottom edge at y=0.
    notch_vertices = [
        (-notch_bottom_width / 2, 0),
        (notch_bottom_width / 2, 0),
        (notch_top_width / 2, notch_height),
        (-notch_top_width / 2, notch_height),
    ]
    notch_c.add_polygon(notch_vertices, layer=layer) # Add the polygon to this component
    
    # 2.3. Use a temporary component to position the notch relative to the main rectangle
    # before performing the boolean operation.
    temp_comp_for_base = gf.Component("temp_base_construction")
    main_rect_ref = temp_comp_for_base << main_rect_c
    notch_ref = temp_comp_for_base << notch_c 
    
    # Position the notch: Its bottom-center (0,0 in its own system) needs to be centered
    # horizontally at the bottom of the main rectangle.
    # The `main_rect_ref`'s bottom-left is at (0,0), its width is `main_block_width`.
    notch_ref.movex(main_block_width / 2) # Moves its center to the center of main_rect_ref's bottom edge

    # 2.4. Perform boolean subtraction to create the final base shape with the notch.
    # Add the resulting base shape component to our main device component.
    base_shape = gf.boolean(
        main_rect_ref, notch_ref, operation="not", layer=layer
    )
    c << base_shape

    # --- 3. Create a single tower component as a reusable sub-cell ---
    @gf.cell
    def create_single_tower(
        cap_width: float,
        cap_height: float,
        taper_top_w: float,
        taper_base_w: float,
        taper_h: float,
        layer,
    ) -> gf.Component:
        """
        Creates a single tower unit, composed of a trapezoidal base and a rectangular top cap.
        The component's reference point (0,0) will be its bottom-center.
        """
        tower_c = gf.Component("single_tower_unit")

        # 3.1. Tapered base part of the tower (trapezoid).
        # Vertices for a trapezoid centered horizontally at x=0, with bottom edge at y=0.
        taper_vertices = [
            (-taper_base_w / 2, 0),
            (taper_base_w / 2, 0),
            (taper_top_w / 2, taper_h),
            (-taper_top_w / 2, taper_h),
        ]
        tower_c.add_polygon(taper_vertices, layer=layer) 

        # 3.2. Top rectangular cap of the tower.
        rect_cap_c = gf.components.rectangle(
            size=(cap_width, cap_height), layer=layer, centered=True
        )
        rect_cap_ref = tower_c << rect_cap_c
        
        # Position the top rectangle: Its bottom edge needs to align with the *top-center*
        # of the tapered base.
        # The taper's top edge is at y = `taper_h`.
        # `rect_cap_ref` is centered, so its center is moved to (`0`, `taper_h + cap_height / 2`).
        rect_cap_ref.movey(taper_h + cap_height / 2)
        
        return tower_c

    # Instantiate the single tower cell with our defined parameters.
    single_tower_c = create_single_tower(
        tower_cap_width,
        tower_cap_height,
        tower_taper_top_width,
        tower_taper_base_width,
        tower_taper_height,
        layer
    )

    # --- 4. Place 4 instances of the tower on top of the main block ---
    num_towers = 4
    
    # Calculate uniform internal spacing for the towers such that they span the entire
    # main_block_width, with no gaps on the outer edges.
    # main_block_width = (num_towers * tower_taper_base_width) + ((num_towers - 1) * internal_gap)
    internal_gap = (main_block_width - (num_towers * tower_taper_base_width)) / (num_towers - 1)
    
    for i in range(num_towers):
        tower_ref = c << single_tower_c
        
        # Calculate the x-position for the current tower's bottom-center.
        # The left edge of the first tower (i=0) is at x=0. Its center is at half its base width.
        # Subsequent towers are placed by adding (full base width + internal gap) repeatedly.
        x_pos = (tower_taper_base_width / 2) + i * (tower_taper_base_width + internal_gap)
        
        # Move the tower. Its bottom-center (0,0 in its own coordinate system)
        # should be moved to (`x_pos`, `main_block_height`) in the parent component's system.
        # This aligns the bottom of the towers with the top of the main block.
        tower_ref.move((x_pos, main_block_height))

    return c

# Create the device
device = custom_device()

# Get the bounding box of the device and print its width and height.
bbox = device.dbbox()
print(f"Generated device footprint: ({bbox.width()}, {bbox.height()})")

# Verify the footprint against the constraint.
# It should be close to (25.0, 10.0)
expected_width = 25.0
expected_height = 10.0
assert abs(bbox.width() - expected_width) < 1e-6, f"Width mismatch: {bbox.width()} != {expected_width}"
assert abs(bbox.height() - expected_height) < 1e-6, f"Height mismatch: {bbox.height()} != {expected_height}"
print("Footprint matches constraint.")

# Save the GDS file
device.write_gds("combined_device.gds")

# Optional: Visualize the GDS layout using KLayout (if installed and configured)
# gf.show(device)