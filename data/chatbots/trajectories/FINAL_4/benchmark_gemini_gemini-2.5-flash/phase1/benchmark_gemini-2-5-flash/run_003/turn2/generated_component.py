import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_parallel_bands():
    """
    Recreates the wavy parallel bands device shown in the new image using GDSFactory.
    This version features a constant gap between the wavy bands and a sine wave shape.
    """
    c = gf.Component("wavy_parallel_bands")

    # --- Device Dimensions ---
    # Assuming the footprint constraint [18, 3] from the previous problem still applies
    device_width = 18.0
    # device_height = 3.0 # Total available height for the device

    # --- Geometric Parameters (estimated from the new image) ---
    # Number of full periods horizontally
    num_periods = 3
    period = device_width / num_periods  # Length of one wave cycle (e.g., 18/3 = 6 um)
    frequency = 2 * np.pi / period      # Angular frequency for the sine function

    # Width of each black band
    band_width = 0.4  # microns

    # Constant width of the white channel (gap) between the two bands
    gap_width = 0.6   # microns

    # Amplitude of the sine wave for the centerlines of the bands
    wave_amplitude = 0.5 # microns (vertical peak deviation from the band's average y-position)

    # --- Calculate Vertical Offsets for Band Centerlines ---
    # The vertical distance between the centerlines of the two bands is the gap plus one band_width.
    centerline_separation = gap_width + band_width

    # Since the entire structure is centered around y=0:
    # The top band's centerline average position
    y_offset_top_band = centerline_separation / 2
    # The bottom band's centerline average position
    y_offset_bottom_band = -centerline_separation / 2

    # --- Generate Path Points ---
    # Use a sufficient number of points to ensure smooth curves
    num_points = 200
    x_points = np.linspace(0, device_width, num_points)

    # Calculate y-coordinates for the centerline of the top black band
    # Using a sine wave: y = Y_offset + Amplitude * sin(frequency * x)
    y_top_band_centerline_points = y_offset_top_band + wave_amplitude * np.sin(frequency * x_points)
    top_band_path_points = np.array([x_points, y_top_band_centerline_points]).T

    # Calculate y-coordinates for the centerline of the bottom black band
    y_bottom_band_centerline_points = y_offset_bottom_band + wave_amplitude * np.sin(frequency * x_points)
    bottom_band_path_points = np.array([x_points, y_bottom_band_centerline_points]).T

    # --- Create Paths and Extrude ---
    # Define the cross-section for the black bands (constant width)
    xs_band = gf.cross_section.cross_section(width=band_width, layer=(1, 0))

    # Create Path objects from the generated points
    path_top = gf.Path(top_band_path_points)
    path_bottom = gf.Path(bottom_band_path_points)

    # Extrude the paths with the defined cross-section to create the black bands
    top_band = c << path_top.extrude(xs_band)
    bottom_band = c << path_bottom.extrude(xs_band)

    # Optional: Verification of total geometry height against assumed footprint
    max_y_geom = y_offset_top_band + wave_amplitude + band_width / 2
    min_y_geom = y_offset_bottom_band - wave_amplitude - band_width / 2
    total_geometry_height = max_y_geom - min_y_geom
    # print(f"Calculated total geometry height: {total_geometry_height:.2f} um (should fit within 3um)")
    # With current parameters: 0.5 + 0.5 + 0.2 - (-0.5 - 0.5 - 0.2) = 1.2 - (-1.2) = 2.4 um.

    return c

# Create the device component
device = wavy_parallel_bands()

# Save the GDSII file
device.write_gds("wavy_parallel_bands.gds")