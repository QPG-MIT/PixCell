import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_parallel_bands_improved():
    """
    Recreates the wavy parallel bands device shown in the original image using GDSFactory.
    This version uses gf.path.smooth to create the wavy paths, allowing for more control
    over the curve's sharpness at turning points to better match the "pinched" look
    of the target image compared to a pure cosine wave.
    """
    c = gf.Component("wavy_parallel_bands_smooth_paths")

    # --- Device Dimensions ---
    device_width = 18.0
    # device_height = 3.0 # Footprint constraint

    # --- Geometric Parameters (estimated from the target image and adjusted for footprint) ---
    num_periods = 2  # Visually, 2 full waves over the width
    
    band_width = 0.6  # Width of each black band
    gap_width = 0.8   # Constant width of the white channel (gap)

    # Calculate wave_amplitude for the *central axis of the white channel*.
    # This ensures the total height fits within the footprint.
    max_device_height_target = 2.9
    wave_amplitude = (max_device_height_target / 2) - (gap_width / 2) - band_width
    # Calculation: (2.9 / 2) - (0.8 / 2) - 0.6 = 1.45 - 0.4 - 0.6 = 0.45 um

    # Vertical distance from the channel's centerline to the band's centerline.
    offset_channel_to_band_center = (gap_width / 2) + (band_width / 2)
    # Calculation: (0.8 / 2) + (0.6 / 2) = 0.4 + 0.3 = 0.7 um

    # --- Path Generation using gf.path.smooth ---

    # Define the key waypoints for the *channel's centerline*.
    # These points represent the extrema (crests/troughs) of the wave.
    # The wave starts at a crest at x=0, goes to a trough at x=4.5, a crest at x=9, etc.
    # We need num_periods * 2 + 1 points to define num_periods waves with crests at ends.
    x_extrema = np.linspace(0, device_width, num_periods * 2 + 1)
    
    # Alternate between wave_amplitude and -wave_amplitude for y-coordinates
    y_extrema_channel_center = []
    for i in range(len(x_extrema)):
        if i % 2 == 0:
            y_extrema_channel_center.append(wave_amplitude) # Crests at x=0, 9, 18
        else:
            y_extrema_channel_center.append(-wave_amplitude) # Troughs at x=4.5, 13.5
            
    channel_center_waypoints = list(zip(x_extrema, y_extrema_channel_center))

    # Offset these waypoints for the top and bottom band centerlines
    top_band_center_waypoints = [(x, y + offset_channel_to_band_center) for x, y in channel_center_waypoints]
    bottom_band_center_waypoints = [(x, y - offset_channel_to_band_center) for x, y in channel_center_waypoints]

    # Define the cross-section for the black bands.
    xs_band = gf.cross_section.cross_section(width=band_width, layer=(1, 0))

    # Create Path objects using gf.path.smooth
    # The 'radius' parameter controls the sharpness of the turns.
    # A smaller radius tends to create visually "sharper" bends closer to the waypoints,
    # which might better match the "pinched" look of the target image.
    smooth_radius = 1.5 # Adjusted for a better visual match

    path_top = gf.path.smooth(points=top_band_center_waypoints, radius=smooth_radius)
    path_bottom = gf.path.smooth(points=bottom_band_center_waypoints, radius=smooth_radius)

    # Extrude the paths to create the black bands geometry.
    c << path_top.extrude(xs_band)
    c << path_bottom.extrude(xs_band)

    # --- Verification of total geometry height (remains consistent) ---
    # Max Y coordinate of the outer edge of the top band at its highest point:
    # (wave_amplitude + offset_channel_to_band_center) + band_width / 2
    # = (0.45 + 0.7) + 0.6 / 2 = 1.15 + 0.3 = 1.45 um
    # Min Y coordinate of the outer edge of the bottom band at its lowest point:
    # (-wave_amplitude - offset_channel_to_band_center) - band_width / 2
    # = (-0.45 - 0.7) - 0.6 / 2 = -1.15 - 0.3 = -1.45 um
    # Total height = 1.45 - (-1.45) = 2.9 um, which fits perfectly within the 3um footprint.

    return c

# Create the device component
device = wavy_parallel_bands_improved()

# Save the GDSII file
device.write_gds("wavy_parallel_bands_improved.gds")