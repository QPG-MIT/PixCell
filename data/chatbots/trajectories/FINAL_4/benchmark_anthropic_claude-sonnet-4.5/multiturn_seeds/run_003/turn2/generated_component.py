import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_bands(
    length: float = 18.0,
    spacing: float = 1.2,
    min_width: float = 0.15,
    max_width: float = 1.3,
    wave_amplitude: float = 0.35,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Create two horizontal wavy bands with varying width.
    
    Args:
        length: Total horizontal length in microns
        spacing: Vertical spacing between the two bands
        min_width: Minimum width of each band at the ends
        max_width: Maximum width of each band in the middle
        wave_amplitude: Amplitude of the wave oscillation
        layer: GDS layer specification
    """
    c = gf.Component()
    
    # Number of points for smooth variation
    num_points = 200
    x_coords = np.linspace(0, length, num_points)
    
    # Create width variation function - dramatic lens/elliptical shape
    # Use parabolic function for smooth width variation (thin → thick → thin)
    normalized_x = (x_coords - length/2) / (length/2)  # -1 to 1
    widths = min_width + (max_width - min_width) * (1 - normalized_x**2)
    
    # Create two bands with opposing wave patterns
    for idx, band_offset in enumerate([spacing / 2, -spacing / 2]):
        top_points = []
        bottom_points = []
        
        # Alternate wave direction for each band (opposing waves)
        wave_direction = 1 if idx == 0 else -1
        
        for i, x in enumerate(x_coords):
            half_width = widths[i] / 2
            # Create sinusoidal wave along the centerline
            y_curve = band_offset + wave_direction * wave_amplitude * np.sin(2 * np.pi * x / length)
            
            top_points.append((x, y_curve + half_width))
            bottom_points.append((x, y_curve - half_width))
        
        # Create closed polygon
        all_points = top_points + bottom_points[::-1]
        
        # Add polygon to component
        c.add_polygon(all_points, layer=layer)
    
    return c

# Create the device
device = wavy_bands()

# Save to GDS
device.write_gds("wavy_bands.gds")

print("GDS file saved as: wavy_bands.gds")