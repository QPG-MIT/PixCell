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
    # Estimated height (e.g., 70% of total height)
    main_block_width = device_width
    main_block_height = 7.0 

    # Dimensions for the V-shaped notch at the bottom center
    notch_width = 2.0
    notch_height = 1.5

    # Dimensions for each of the four towers
    # Each tower consists of a narrow rectangular top and a wider tapered base.
    tower_top_width = 1.5
    tower_top_height = 0.5
    # The height of the tapered part is the remaining height after main block and top rect.
    tower_taper_height = device_height - main_block_height - tower_top_height # 10.0 - 7.0 - 0.5 = 2.5
    tower_taper_bottom_width = 3.5 # The widest part of the tower's base

    # --- 2. Create the main block (rectangle with a notch subtracted) ---
    # 2.1. Create the initial large rectangular base.
    # `centered=False` places its bottom-left corner at (0,0).
    main_rect_c = gf.components.rectangle(
        size=(main_block_width, main_block_height), layer=layer, centered=False
    )
    
    # 2.2. Create the triangular notch component.
    # `gf.components.triangle(x, y)` creates a triangle with vertices at (0,0), (x,0), and (x/2,y).
    notch_triangle_c = gf.components.triangle(
        x=notch_width, y=notch_height, layer=layer
    )
    
    # 2.3. Use a temporary component to position the notch relative to the main rectangle
    # before performing the boolean operation.
    temp_comp_for_base = gf.Component("temp_base_construction")
    main_rect_ref = temp_comp_for_base << main_rect_c
    notch_triangle_ref = temp_comp_for_base << notch_triangle_c
    
    # Position the notch: Its base (which is along y=0 from its definition)
    # needs to be centered horizontally at the bottom of the main rectangle.
    # main_rect_ref's bottom-left is at (0,0), its width is `main_block_width`.
    notch_triangle_ref.movex(main_block_width / 2 - notch_width / 2)
    # The notch's base is already at y=0, so no vertical movement is needed.

    # 2.4. Perform boolean subtraction to create the final base shape with the notch.
    # It's important to add the resulting boolean component to 'c' directly, 
    # as `gf.boolean` returns a new component, not a reference to an existing one.
    base_shape = gf.boolean(
        main_rect_ref, notch_triangle_ref, operation="not", layer=layer
    )
    # Add the resulting base shape component to our main device component.
    c << base_shape

    # --- 3. Create a single tower component as a reusable sub-cell ---
    @gf.cell
    def create_single_tower(
        top_width: float,
        top_height: float,
        taper_height: float,
        taper_bottom_width: float,
        layer,
    ) -> gf.Component:
        """
        Creates a single tower unit, composed of a tapered base and a rectangular top.
        The component's reference point (0,0) will be its bottom-center.
        """
        tower_c = gf.Component("single_tower_unit")

        # 3.1. Tapered base part of the tower.
        # gf.components.taper creates a trapezoidal shape. By default, it's horizontal,
        # with 'width1' at (0,0) and 'width2' at (length,0).
        # We want: bottom (wider) at y=0, top (narrower) at y=taper_height.
        # So, we set width1 as `taper_bottom_width` and width2 as `top_width`,
        # and `length` as `taper_height`.
        taper_horiz_c = gf.components.taper(
            length=taper_height,
            width1=taper_bottom_width,
            width2=top_width,
            layer=layer,
        )
        taper_ref = tower_c << taper_horiz_c
        # Rotate the taper by 90 degrees counter-clockwise to make it vertical.
        # After rotation, its bottom (width1) is centered at (0,0), and its top (width2)
        # is centered at (0, `taper_height`).
        taper_ref.rotate(90) 

        # 3.2. Top rectangular part of the tower.
        # `centered=True` places its center at (0,0).
        rect_top_c = gf.components.rectangle(
            size=(top_width, top_height), layer=layer, centered=True
        )
        rect_top_ref = tower_c << rect_top_c
        
        # Position the top rectangle: Its bottom edge needs to align perfectly
        # with the top edge of the tapered base.
        # The taper's top edge is at y = `taper_height`.
        # A centered rectangle has its bottom edge at y = -`top_height` / 2.
        # So, we move it up by (`taper_height` + `top_height` / 2).
        rect_top_ref.movey(taper_height + top_height / 2)
        
        # The `single_tower_unit` component now has its overall bottom-center at (0,0).
        return tower_c

    # Instantiate the single tower cell with our defined parameters.
    single_tower_c = create_single_tower(
        tower_top_width, tower_top_height, tower_taper_height, tower_taper_bottom_width, layer
    )

    # --- 4. Place 4 instances of the tower on top of the main block ---
    num_towers = 4
    
    # Calculate uniform spacing for the towers across the `main_block_width`.
    # There are `num_towers` towers, each of base width `tower_taper_bottom_width`.
    # This leaves `main_block_width - (num_towers * tower_taper_bottom_width)` space.
    # This remaining space is distributed among `(num_towers - 1)` internal gaps
    # and 2 edge gaps (one on each side). Total number of gaps = `num_towers + 1`.
    total_towers_base_width = num_towers * tower_taper_bottom_width
    remaining_space_for_gaps = main_block_width - total_towers_base_width
    gap_spacing = remaining_space_for_gaps / (num_towers + 1)

    for i in range(num_towers):
        tower_ref = c << single_tower_c
        
        # Calculate the x-position for the current tower's bottom-center.
        # For the first tower (i=0): `gap_spacing` (left edge) + `tower_taper_bottom_width / 2` (center).
        # For subsequent towers, add `(tower_taper_bottom_width + gap_spacing)` for each step.
        x_pos = gap_spacing + (tower_taper_bottom_width / 2) + i * (tower_taper_bottom_width + gap_spacing)
        
        # Place the tower. Its bottom-center (0,0 in its own coordinate system)
        # should be moved to (`x_pos`, `main_block_height`) in the parent component's system.
        # This aligns the bottom of the towers with the top of the main block.
        tower_ref.move((x_pos, main_block_height))

    return c

# Create the device
device = custom_device()

# Get the bounding box of the device and print its width and height.
# GDSFactory components use .dbbox() to get the bounding box,
# which has .width() and .height() methods.
bbox = device.dbbox()
print(f"Generated device footprint: ({bbox.width()}, {bbox.height()})") # Expected: (25.0, 10.0)

# Save the GDS file
device.write_gds("combined_device.gds")

# Optional: Visualize the GDS layout using KLayout (if installed and configured)
# gf.show(device)