import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_parallel_bands():
    """
    Recreates the wavy parallel bands device shown in the original image using GDSFactory.
    This version uses explicit cosine wave functions to generate smooth, continuous paths
    for the two parallel bands, ensuring a constant gap between their edges.
    """
    c = gf.Component("wavy_parallel_bands_sine_constant_gap")

    # --- Device Dimensions ---
    device_width = 18.0
    # device_height = 3.0 # Footprint constraint

    # --- Geometric Parameters (estimated from the target image and adjusted for footprint) ---
    num_periods = 2  # Visually, about 2 full waves (crest-to-crest) over the width
    period_length = device_width / num_periods  # Length of one wave cycle (18/2 = 9 um)

    band_width = 0.6  # Width of each black band (adjusted for better visual match)
    gap_width = 0.8   # Constant width of the white channel (gap) between the two bands (adjusted)

    # Calculate wave_amplitude for the *central axis of the white channel*.
    # The total height (H) of the device is determined by the oscillation amplitude,
    # the gap width, and the band widths.
    # H = 2 * (amplitude_of_channel_centerline_wave + vertical_offset_from_channel_center_to_band_outer_edge)
    # The vertical offset from the channel center to the band's outer edge is (gap_width / 2) + band_width.
    # So, H = 2 * (wave_amplitude + gap_width / 2 + band_width)
    # Let's aim for 2.9um total height to leave a small margin within the 3um footprint.
    max_device_height_target = 2.9
    wave_amplitude = (max_device_height_target / 2) - (gap_width / 2) - band_width
    # Calculation: (2.9 / 2) - (0.8 / 2) - 0.6 = 1.45 - 0.4 - 0.6 = 0.45 um

    # --- Path Generation ---
    num_points = 500  # Number of points to sample the sine wave for smooth rendering
    x_coords = np.linspace(0, device_width, num_points)

    # Vertical distance from the channel's centerline to the band's centerline.
    # This value is constant, ensuring the two bands remain parallel.
    offset_channel_to_band_center = (gap_width / 2) + (band_width / 2)
    # Calculation: (0.8 / 2) + (0.6 / 2) = 0.4 + 0.3 = 0.7 um

    top_band_center_points = []
    bottom_band_center_points = []

    for x in x_coords:
        # Define the Y-coordinate for the centerline of the white channel.
        # Using cosine ensures that the channel is at its vertical extrema (pinch points)
        # at x=0 and x=device_width, matching the visual of the target image.
        y_channel_center = wave_amplitude * np.cos(2 * np.pi * x / period_length)

        # Calculate the centerline points for the top and bottom bands.
        # These paths are simply parallel offsets from the y_channel_center path.
        y_top_band_center = y_channel_center + offset_channel_to_band_center
        top_band_center_points.append((x, y_top_band_center))

        y_bottom_band_center = y_channel_center - offset_channel_to_band_center
        bottom_band_center_points.append((x, y_bottom_band_center))

    # --- Create Paths and Extrude ---
    # Define the cross-section for the black bands.
    # It has a constant width and is on layer (1, 0).
    xs_band = gf.cross_section.cross_section(width=band_width, layer=(1, 0))

    # Create Path objects from the generated centerline points.
    path_top = gf.Path(top_band_center_points)
    path_bottom = gf.Path(bottom_band_center_points)

    # Extrude the paths with the defined cross-section to create the black bands geometry.
    c << path_top.extrude(xs_band)
    c << path_bottom.extrude(xs_band)

    # --- Verification of total geometry height ---
    # Max Y coordinate of the outer edge of the top band at its highest point:
    # (wave_amplitude + offset_channel_to_band_center) + band_width / 2
    # = (0.45 + 0.7) + 0.6 / 2 = 1.15 + 0.3 = 1.45 um
    # Min Y coordinate of the outer edge of the bottom band at its lowest point:
    # (-wave_amplitude - offset_channel_to_band_center) - band_width / 2
    # = (-0.45 - 0.7) - 0.6 / 2 = -1.15 - 0.3 = -1.45 um
    # Total height = 1.45 - (-1.45) = 2.9 um, which fits perfectly within the 3um footprint.

    return c

# Create the device component
device = wavy_parallel_bands()

# Save the GDSII file
device.write_gds("wavy_parallel_bands.gds")