import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_parallel_bands():
    """
    Recreates the wavy parallel bands device shown in the original image using GDSFactory.
    This version features a constant gap between the wavy bands and an S-like wave shape
    achieved using gf.path.smooth.
    """
    c = gf.Component("wavy_parallel_bands_smooth")

    # --- Device Dimensions ---
    device_width = 18.0
    # device_height = 3.0 # Footprint constraint

    # --- Geometric Parameters (estimated from the target image and adjusted for footprint) ---
    num_periods = 2  # Visually, about 2 full waves (crest-to-crest) over the width
    period_length = device_width / num_periods  # Length of one wave cycle (18/2 = 9 um)

    band_width = 0.4  # Width of each black band (kept from previous turn for consistency, visually might be slightly thicker)
    gap_width = 0.6   # Constant width of the white channel (gap) between the two bands (kept from previous turn)

    # Calculate wave_amplitude to fit within the 3um height footprint.
    # Total height (H) = gap_width + 2*band_width + 2*wave_amplitude
    # Let's aim for 2.9um total height to leave a small margin:
    max_device_height_target = 2.9
    wave_amplitude = (max_device_height_target - gap_width - 2 * band_width) / 2
    # Calculation: (2.9 - 0.6 - 2*0.4) / 2 = (2.9 - 0.6 - 0.8) / 2 = 1.5 / 2 = 0.75 um

    # Radius for the smooth bends within gf.path.smooth.
    # This value dictates how "sharp" or "smooth" the S-bends are.
    smooth_bend_radius = 1.5 # Empirically chosen to give a good S-shape

    # --- Calculate Vertical Offsets for Band Centerlines ---
    # The vertical distance between the centerlines of the two bands is the gap plus one band_width.
    centerline_separation = gap_width + band_width # 0.6 + 0.4 = 1.0 um

    # Center the entire structure vertically around y=0
    y_offset_top_band = centerline_separation / 2    # 0.5 um
    y_offset_bottom_band = -centerline_separation / 2 # -0.5 um

    # --- Generate Path Waypoints for gf.path.smooth ---
    # We define key points for the path: crests, troughs, and zero-crossing points.
    # A full period (crest-to-crest) consists of 4 segments defined by 5 points.

    top_band_waypoints = []
    bottom_band_waypoints = []

    # Top band path: Starts at a crest (max Y) and goes through num_periods cycles
    for i in range(num_periods):
        x_segment_start = i * period_length
        # Crest point
        top_band_waypoints.append((x_segment_start, y_offset_top_band + wave_amplitude))
        # Downward zero-crossing point
        top_band_waypoints.append((x_segment_start + period_length/4, y_offset_top_band))
        # Trough point
        top_band_waypoints.append((x_segment_start + period_length/2, y_offset_top_band - wave_amplitude))
        # Upward zero-crossing point
        top_band_waypoints.append((x_segment_start + 3*period_length/4, y_offset_top_band))
    # Add the final crest point at the end of the last period
    top_band_waypoints.append((num_periods * period_length, y_offset_top_band + wave_amplitude))


    # Bottom band path: Starts at a trough (min Y) to be in antiphase with the top band,
    # creating the characteristic narrowing/widening channel.
    for i in range(num_periods):
        x_segment_start = i * period_length
        # Trough point
        bottom_band_waypoints.append((x_segment_start, y_offset_bottom_band - wave_amplitude))
        # Upward zero-crossing point
        bottom_band_waypoints.append((x_segment_start + period_length/4, y_offset_bottom_band))
        # Crest point
        bottom_band_waypoints.append((x_segment_start + period_length/2, y_offset_bottom_band + wave_amplitude))
        # Downward zero-crossing point
        bottom_band_waypoints.append((x_segment_start + 3*period_length/4, y_offset_bottom_band))
    # Add the final trough point at the end of the last period
    bottom_band_waypoints.append((num_periods * period_length, y_offset_bottom_band - wave_amplitude))

    # --- Create Paths and Extrude ---
    # Define the cross-section for the black bands (constant width and layer)
    xs_band = gf.cross_section.cross_section(width=band_width, layer=(1, 0))

    # Create Path objects using gf.path.smooth to connect the waypoints with smooth bends
    path_top = gf.path.smooth(top_band_waypoints, radius=smooth_bend_radius)
    path_bottom = gf.path.smooth(bottom_band_waypoints, radius=smooth_bend_radius)

    # Extrude the paths with the defined cross-section to create the black bands
    top_band_component = c << path_top.extrude(xs_band)
    bottom_band_component = c << path_bottom.extrude(xs_band)

    # --- Verification of total geometry height against assumed footprint ---
    # Max Y coordinate of the top band: y_offset_top_band + wave_amplitude + band_width / 2
    # Min Y coordinate of the bottom band: y_offset_bottom_band - wave_amplitude - band_width / 2
    # With current parameters:
    # Max Y = 0.5 + 0.75 + 0.4/2 = 0.5 + 0.75 + 0.2 = 1.45 um
    # Min Y = -0.5 - 0.75 - 0.4/2 = -0.5 - 0.75 - 0.2 = -1.45 um
    # Total height = 1.45 - (-1.45) = 2.9 um, which fits within the 3um footprint.

    return c

# Create the device component
device = wavy_parallel_bands()

# Save the GDSII file
device.write_gds("wavy_parallel_bands.gds")