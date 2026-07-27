import gdsfactory as gf
import numpy as np

# Define a custom cross_section layer for the black stripes.
X_LAYER = (1, 0)

@gf.cell
def custom_wavy_channels_inverse():
    """
    Creates two wavy, parallel black channels with an INVERTED gap behavior
    compared to the provided image, fitting within a 18x3 µm footprint.

    In this version:
    - The white channel (gap) is WIDEST at the center.
    - The white channel (gap) is NARROWESt at the ends.
    - The top black line curves UPWARDS at the center and DOWNWARDS at the ends.
    - The bottom black line curves DOWNWARDS at the center and UPWARDS at the ends.

    This is provided as an alternative interpretation since the previous code
    already matched the visual geometry of the "original image".
    """
    c = gf.Component("wavy_channels_inverse")

    # 1. Define overall dimensions and features based on the image and footprint
    total_width = 18.0  # Total horizontal extent of the device [µm]
    total_height = 3.0  # Total vertical extent of the device [µm]
    
    stripe_width = 0.5  # Fixed width (thickness) of each black line [µm]
    
    # For the INVERSE pattern:
    # max_gap is the widest gap (at the center)
    # min_gap is the narrowest gap (at the ends)
    min_gap_at_ends = 0.5       # Narrowest vertical gap between the lines (at the ends) [µm]
    max_gap_at_center = 1.5     # Widest vertical gap between the lines (at the center) [µm]

    # --- 2. Derived Parameters for Path Generation ---
    
    # X-coordinates range from -total_width/2 to total_width/2, centered at 0
    x_min = -total_width / 2  # -9.0 µm
    x_max = total_width / 2   # 9.0 µm
    
    # Number of points to define the curve for smooth extrusion. More points = smoother curve.
    num_points = 200 
    x_coords = np.linspace(x_min, x_max, num_points)

    # Calculate target y-coordinates for the *centerline* of the top stripe path:
    # At x=0 (device center), the gap is `max_gap_at_center`.
    #   Top stripe's center y: max_gap_at_center/2 + stripe_width/2
    y_center_at_mid_target = max_gap_at_center / 2 + stripe_width / 2 # (1.5/2 + 0.5/2 = 1.0 µm)

    # At x=x_min or x_max (device ends), the gap is `min_gap_at_ends`.
    #   Top stripe's center y: min_gap_at_ends/2 + stripe_width/2
    y_center_at_edge_target = min_gap_at_ends / 2 + stripe_width / 2 # (0.5/2 + 0.5/2 = 0.5 µm)
    
    # Define the curve using y(x) = y_offset + amplitude * cos(frequency * x)
    # This formula creates a curve that is high at x=0 (cos(0)=1) and low at x=±width/2 (cos(±π)=-1).
    y_offset_for_path = (y_center_at_mid_target + y_center_at_edge_target) / 2  # (1.0 + 0.5) / 2 = 0.75 µm
    amplitude_for_path = (y_center_at_mid_target - y_center_at_edge_target) / 2 # (1.0 - 0.5) / 2 = 0.25 µm
    
    # The cosine argument needs to go from -π to π over the range [x_min, x_max].
    # So, frequency * x_max = π  => frequency = π / (total_width / 2)
    frequency = np.pi / (total_width / 2) # π / 9.0

    # 3. Generate points for the top stripe's centerline path
    # Using +amplitude_for_path * np.cos to make it highest at center, lowest at ends
    y_coords_top = y_offset_for_path + amplitude_for_path * np.cos(frequency * x_coords)
    points_top = [(x, y) for x, y in zip(x_coords, y_coords_top)]

    # 4. Generate points for the bottom stripe's centerline path (vertically symmetric)
    points_bottom = [(x, -y) for x, y in points_top]

    # 5. Create GDSFactory Path objects from the generated points
    path_top = gf.Path(points_top)
    path_bottom = gf.Path(points_bottom)

    # 6. Define the cross-section for the black stripes
    cross_section = gf.cross_section.cross_section(width=stripe_width, layer=X_LAYER)

    # 7. Extrude the paths to create the GDS geometry (ComponentReferences)
    top_stripe = c << gf.path.extrude(path_top, cross_section=cross_section)
    bottom_stripe = c << gf.path.extrude(path_bottom, cross_section=cross_section)

    # 8. Validate the final footprint
    # Max Y-coordinate of the top stripe's top edge: y_center_at_mid_target + stripe_width/2 = 1.0 + 0.25 = 1.25 µm
    # Min Y-coordinate of the bottom stripe's bottom edge: -(y_center_at_mid_target + stripe_width/2) = -1.25 µm
    # Actual device height: 1.25 - (-1.25) = 2.5 µm.
    # Actual device width: x_max - x_min = 9 - (-9) = 18.0 µm.
    # This fits perfectly within the 18x3 µm footprint, leaving 0.25 µm vertical padding on each side.
    
    return c

# Create the component
device_inverse = custom_wavy_channels_inverse()

# Write the component to a GDSII file
device_inverse.write_gds("wavy_channels_inverse.gds")

# Optional: To visualize the GDS layout (requires KLayout or similar viewer setup)
# device_inverse.show()