import gdsfactory as gf
import numpy as np

# Define a custom cross_section layer for the black stripes.
X_LAYER = (1, 0)

@gf.cell
def custom_wavy_channels():
    """
    Creates two wavy, parallel black channels matching the provided image,
    fitting within a 18x3 µm footprint.

    In this version:
    - The white channel (gap) is NARROWEST at the center.
    - The white channel (gap) is WIDEST at the ends.
    - The top black line curves DOWNWARDS at the center and UPWARDS at the ends.
    - The bottom black line curves UPWARDS at the center and DOWNWARDS at the ends.
    """
    c = gf.Component("wavy_channels")

    # 1. Define overall dimensions and features based on the image and footprint
    total_width = 18.0  # Total horizontal extent of the device [µm]
    total_height = 3.0  # Total vertical extent of the device [µm]
    
    stripe_width = 0.5  # Fixed width (thickness) of each black line [µm]
    
    # For the TARGET pattern:
    # center_gap is the NARROWEST gap (at the center, x=0)
    # end_gap is the WIDEST gap (at the ends, x=+-total_width/2)
    center_gap = 0.5            # Narrowest vertical gap between the lines (at the center) [µm]
    end_gap = 1.5               # Widest vertical gap between the lines (at the ends) [µm]

    # --- 2. Derived Parameters for Path Generation ---
    
    # X-coordinates range from -total_width/2 to total_width/2, centered at 0
    x_min = -total_width / 2  # -9.0 µm
    x_max = total_width / 2   # 9.0 µm
    
    num_points = 200 
    x_coords = np.linspace(x_min, x_max, num_points)

    # Calculate target y-coordinates for the *centerline* of the top stripe path:
    # At x=0 (device center), the gap is `center_gap`.
    #   Top stripe's centerline y-coordinate: center_gap/2 + stripe_width/2
    y_centerline_at_mid = center_gap / 2 + stripe_width / 2 # (0.5/2 + 0.5/2 = 0.25 + 0.25 = 0.5 µm)

    # At x=x_min or x_max (device ends), the gap is `end_gap`.
    #   Top stripe's centerline y-coordinate: end_gap/2 + stripe_width/2
    y_centerline_at_edge = end_gap / 2 + stripe_width / 2   # (1.5/2 + 0.5/2 = 0.75 + 0.25 = 1.0 µm)
    
    # Define the curve using y(x) = y_offset + amplitude * cos(frequency * x)
    # y_offset is the average y-value of the centerline.
    y_offset_for_path = (y_centerline_at_mid + y_centerline_at_edge) / 2  # (0.5 + 1.0) / 2 = 0.75 µm
    
    # Amplitude for the cosine function.
    # To make the curve lowest at the center (where cos(0)=1) and highest at the ends (where cos(±π)=-1),
    # the amplitude must be NEGATIVE.
    amplitude_for_path = (y_centerline_at_mid - y_centerline_at_edge) / 2 # (0.5 - 1.0) / 2 = -0.25 µm
    
    # The cosine argument needs to go from -π to π over the range [x_min, x_max].
    # So, frequency * x_max = π  => frequency = π / (total_width / 2)
    frequency = np.pi / (total_width / 2) # π / 9.0

    # 3. Generate points for the top stripe's centerline path
    # With amplitude_for_path being negative, it correctly makes the curve lowest at center (cos(0)=1)
    # and highest at ends (cos(±π)=-1).
    y_coords_top = y_offset_for_path + amplitude_for_path * np.cos(frequency * x_coords)
    points_top = [(x, y) for x, y in zip(x_coords, y_coords_top)]

    # 4. Generate points for the bottom stripe's centerline path (vertically symmetric)
    # Negating y for the bottom stripe automatically creates the symmetric inverted curve.
    points_bottom = [(x, -y) for x, y in points_top]

    # 5. Create GDSFactory Path objects from the generated points
    path_top = gf.Path(points_top)
    path_bottom = gf.Path(points_bottom)

    # 6. Define the cross-section for the black stripes
    cross_section = gf.cross_section.cross_section(width=stripe_width, layer=X_LAYER)

    # 7. Extrude the paths to create the GDS geometry (ComponentReferences)
    top_stripe = c << gf.path.extrude(path_top, cross_section=cross_section)
    bottom_stripe = c << gf.path.extrude(path_bottom, cross_section=cross_section)

    # 8. Validate the final footprint (as a check, not part of the design)
    # Max Y-coordinate of the top stripe's top edge (at ends): y_centerline_at_edge + stripe_width/2 = 1.0 + 0.25 = 1.25 µm
    # Min Y-coordinate of the bottom stripe's bottom edge (at ends): -(y_centerline_at_edge + stripe_width/2) = -1.25 µm
    # Actual device height: 1.25 - (-1.25) = 2.5 µm.
    # Actual device width: x_max - x_min = 9 - (-9) = 18.0 µm.
    # This fits perfectly within the 18x3 µm footprint, leaving 0.25 µm vertical padding on each side.
    
    return c

# Create the component
device = custom_wavy_channels()

# Write the component to a GDSII file
device.write_gds("wavy_channels.gds")