import gdsfactory as gf
from typing import Tuple # Import Tuple for type hinting

# Define a custom layer for the device
DEVICE_LAYER = (1, 0)

@gf.cell
def create_tower(
    width_top: float,
    width_bottom: float,
    height_top_rect: float,
    height_taper: float,
    height_bottom_rect: float,
    layer: Tuple[int, int],
) -> gf.Component:
    """
    Creates a single tower component composed of a bottom rectangle, a middle taper,
    and a top rectangle. The component's (0,0) is its bottom-center.
    """
    c = gf.Component()

    # Bottom rectangle: forms the base of the tower
    ref_rect_bottom = c << gf.components.rectangle(
        size=(width_bottom, height_bottom_rect), layer=layer, centered=True
    )
    # Move so its bottom edge is at y=0, effectively making the tower's bottom-center the origin
    ref_rect_bottom.movey(height_bottom_rect / 2)

    # Tapered middle section: connects the bottom and top rectangles
    # gf.components.taper creates a trapezoid: width1 (bottom) to width2 (top) over length
    ref_taper_mid = c << gf.components.taper(
        length=height_taper,
        width1=width_bottom,  # Wider bottom of the taper
        width2=width_top,     # Narrower top of the taper
        layer=layer,
        centered=True,
    )
    # Move to stack directly on top of the bottom rectangle
    ref_taper_mid.movey(height_bottom_rect + height_taper / 2)

    # Top rectangle: the narrowest part at the very top of the tower
    ref_rect_top = c << gf.components.rectangle(
        size=(width_top, height_top_rect), layer=layer, centered=True
    )
    # Move to stack directly on top of the tapered section
    ref_rect_top.movey(height_bottom_rect + height_taper + height_top_rect / 2)

    return c


@gf.cell
def my_device_from_primitives() -> gf.Component:
    """
    Recreates the device geometry from the PNG image using GDSFactory parametric functions.
    The device is centered at (0,0) with a footprint of 25x10 um.
    """
    c = gf.Component()
    layer = DEVICE_LAYER

    # --- 1. Define overall dimensions and coordinate system ---
    total_width = 25.0
    total_height = 10.0
    # Device spans x: [-12.5, 12.5], y: [-5, 5]

    # --- 2. Create and position the main body rectangle ---
    W_MB = total_width
    H_MB = 7.0  # Main body height
    
    # Get the primitive rectangle component.
    # IMPORTANT: Create a mutable copy before modifying its internal polygons.
    main_body_comp = gf.components.rectangle(size=(W_MB, H_MB), layer=layer, centered=True).copy()
    
    # Main body will span y from -5 to 2. Its center will be at (0, -1.5).
    # Move the component's internal polygons to the correct absolute position for boolean operation
    main_body_comp.movey(-1.5)

    # --- 3. Create and position the bottom V-notch ---
    notch_width = 2.0
    notch_depth = 1.0
    
    # Get the primitive taper component.
    # IMPORTANT: Create a mutable copy before modifying its internal polygons.
    notch_comp = gf.components.taper(
        length=notch_depth,
        width1=notch_width,  # Base of the triangle (at y=-5)
        width2=0.0,          # Tip of the triangle (at y=-6)
        layer=layer,
        centered=True,       # Taper is centered horizontally at (0,0) initially
    ).copy() # Make a copy

    # Rotate -90 degrees to make it vertical, pointing downwards.
    # After rotation, width1 (base) is at y=length/2, width2 (tip) is at y=-length/2.
    notch_comp.rotate(-90)
    # Current base (top edge) is at y = notch_depth / 2 = 0.5.
    # Target base position is y = -5. So, move by (-5) - 0.5 = -5.5.
    notch_comp.movey(-5.5) # Move the component's internal polygons

    # --- 4. Perform boolean subtraction for main body with notch ---
    # gf.boolean operates on the Component objects' polygons directly.
    base_with_notch = gf.boolean(main_body_comp, notch_comp, operation="not", layer=layer)
    c << base_with_notch  # Add the resulting component to the main device

    # --- 5. Create and array the towers ---
    W_tower_top = 1.5
    W_tower_bottom = 3.0
    H_tower_top_rect = 0.5
    H_taper = 1.5
    H_tower_bottom_rect = 1.0
    # tower_total_height = H_tower_top_rect + H_taper + H_tower_bottom_rect = 3.0

    # Create one tower component (its bottom-center will be at (0,0))
    tower_instance = create_tower(
        W_tower_top, W_tower_bottom, H_tower_top_rect, H_taper, H_tower_bottom_rect, layer=layer
    )

    # Define spacing parameters for the array of 4 towers
    num_towers = 4
    gap_between_towers = 3.0
    side_gap = 2.0

    # Towers sit on top of the main body, so their bottom edge is at y=2.0
    tower_bottom_y = 2.0

    # Calculate the origin for the gf.add_array function.
    # The `origin` parameter specifies the bottom-left coordinate of the *first* instance.
    # The first tower's bottom-left x-coordinate is:
    #   -12.5 (left edge of device) + side_gap = -10.5
    # The first tower's bottom-left y-coordinate is tower_bottom_y = 2.0
    array_origin_x = -total_width / 2 + side_gap
    array_origin_y = tower_bottom_y

    # Calculate the spacing between columns (center-to-center for towers):
    # This is one tower's bottom width plus the gap between towers.
    array_spacing_x = W_tower_bottom + gap_between_towers

    c.add_array(
        component=tower_instance,
        columns=num_towers,
        rows=1,  # Only one row of towers
        spacing=(array_spacing_x, 0), # (x_spacing, y_spacing)
        origin=(array_origin_x, array_origin_y),
    )

    return c

if __name__ == "__main__":
    # Create the device
    device = my_device_from_primitives()

    # Verify footprint and centering
    bounds = device.bbox
    actual_width = bounds[1][0] - bounds[0][0]
    actual_height = bounds[1][1] - bounds[0][1]
    center_x = (bounds[1][0] + bounds[0][0]) / 2
    center_y = (bounds[1][1] + bounds[0][1]) / 2

    print(f"Device bounds: {bounds}")
    print(f"Actual device width: {actual_width:.3f} um")
    print(f"Actual device height: {actual_height:.3f} um")
    print(f"Actual device center: ({center_x:.3f}, {center_y:.3f})")

    # Assertions for footprint constraint
    assert abs(actual_width - 25.0) < 1e-3, f"Width mismatch: Expected 25.0, got {actual_width}"
    assert abs(actual_height - 10.0) < 1e-3, f"Height mismatch: Expected 10.0, got {actual_height}"
    assert abs(center_x) < 1e-3, f"Center X mismatch: Expected 0.0, got {center_x}"
    assert abs(center_y) < 1e-3, f"Center Y mismatch: Expected 0.0, got {center_y}"

    print("\nFootprint and centering verified successfully!")

    # Optional: Display the device (requires KLayout installed and configured)
    # device.show()
    
    # Optional: Save the GDS file
    # device.write_gds("my_parametric_device.gds")