import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_channel_device():
    """
    Recreates the wavy channel device shown in the image using GDSFactory.

    The device consists of two black wavy bands, with a white channel between them
    that narrows at the ends and in the middle, and widens at quarter points.
    """
    c = gf.Component("wavy_channel_device")

    # --- Device Dimensions and Wave Parameters ---
    device_width = 18.0  # From footprint_um[0]
    # device_height = 3.0 # From footprint_um[1], used for bounding box, not geometry generation directly

    # The image shows two full periods of the wave
    num_periods = 2
    period = device_width / num_periods  # Length of one wave cycle
    frequency = 2 * np.pi / period      # Angular frequency for the cosine function

    # --- Geometric Parameters (estimated from image) ---
    # Width of the black bands
    band_width = 0.5  # microns

    # White channel (gap) dimensions
    min_gap_width = 0.2  # Minimum gap width at x=0, 9, 18 microns
    max_gap_width = 1.0  # Maximum gap width at x=4.5, 13.5 microns

    # --- Calculate Parameters for Centerlines ---
    # The white channel is symmetric around y=0.
    # The y-coordinate for the *bottom edge of the top band* (top of gap) varies sinusoidally.
    # Let y_top_curve(x) = Y_offset - A_wave * cos(frequency * x)
    # The lowest point of y_top_curve (when cos=1) is min_gap_width/2.
    # The highest point of y_top_curve (when cos=-1) is max_gap_width/2.
    
    # Amplitude of the wave for the channel's edges (half of the variation in half the gap)
    amplitude_channel_wave = (max_gap_width / 2 - min_gap_width / 2) / 2
    # Vertical offset for the channel's edges (center of the y-range for half the gap)
    offset_channel_wave = (min_gap_width / 2 + max_gap_width / 2) / 2

    # The centerline of the top band is (band_width / 2) above y_top_curve(x).
    # The centerline of the bottom band is (band_width / 2) below y_bottom_curve(x) = -y_top_curve(x).

    # Vertical shift for the top band's centerline
    vertical_shift_top_centerline = offset_channel_wave + band_width / 2
    # Vertical shift for the bottom band's centerline
    vertical_shift_bottom_centerline = -offset_channel_wave - band_width / 2

    # The amplitude of the wave for the centerlines remains the same as for the channel edges.
    amplitude_centerline_wave = amplitude_channel_wave

    # --- Generate Path Points ---
    # Use enough points to ensure smooth curves
    num_points = 200
    x_points = np.linspace(0, device_width, num_points)

    # Calculate y-coordinates for the centerline of the top black band
    # y = Y_shift - Amplitude * cos(k*x)
    y_top_band_centerline_points = vertical_shift_top_centerline - amplitude_centerline_wave * np.cos(frequency * x_points)
    top_band_path_points = np.array([x_points, y_top_band_centerline_points]).T

    # Calculate y-coordinates for the centerline of the bottom black band
    # y = Y_shift + Amplitude * cos(k*x) (due to mirroring and subtracting width)
    y_bottom_band_centerline_points = vertical_shift_bottom_centerline + amplitude_centerline_wave * np.cos(frequency * x_points)
    bottom_band_path_points = np.array([x_points, y_bottom_band_centerline_points]).T

    # --- Create Paths and Extrude ---
    # Define the cross-section for the black bands (constant width)
    xs_band = gf.cross_section.cross_section(width=band_width, layer=(1, 0))

    # Create Path objects
    path_top = gf.Path(top_band_path_points)
    path_bottom = gf.Path(bottom_band_path_points)

    # Extrude the paths to create the black bands
    top_band = c << path_top.extrude(xs_band)
    bottom_band = c << path_bottom.extrude(xs_band)

    # The paths are generated from x=0 to x=device_width, centered vertically around y=0.
    # The total vertical extent of the generated geometry will be from y=-1.0 to y=1.0 (2um height).
    # This fits within the 3um footprint, with 0.5um padding on top and bottom.
    
    return c

# Create the device component
device = wavy_channel_device()

# Save the GDSII file
device.write_gds("wavy_channel_device.gds")

# Optional: Display the component (requires KLayout or similar viewer)
# gf.show(device)