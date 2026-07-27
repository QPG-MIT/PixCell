import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_ribbons():
    """Create three ribbons - two wavy and one straight."""
    c = gf.Component()
    
    # Parameters
    length = 40.0
    total_height = 1.7
    n_points = 600
    
    x = np.linspace(0, length, n_points)
    
    # Top ribbon - sinusoidal wave with uniform width
    y_center_1 = 0.55
    amplitude_1 = 0.06
    wavelength_1 = 7.5
    width_1 = 0.10
    
    y_wave_1 = y_center_1 + amplitude_1 * np.sin(2 * np.pi * x / wavelength_1)
    y_top_1 = y_wave_1 + width_1 / 2
    y_bot_1 = y_wave_1 - width_1 / 2
    
    points_1 = list(zip(x, y_top_1)) + list(zip(x[::-1], y_bot_1[::-1]))
    c.add_polygon(points_1, layer=(1, 0))
    
    # Middle ribbon - thick and straight
    y_center_2 = 0.0
    width_2 = 0.14
    
    points_2 = [
        (0, y_center_2 - width_2/2),
        (length, y_center_2 - width_2/2),
        (length, y_center_2 + width_2/2),
        (0, y_center_2 + width_2/2)
    ]
    c.add_polygon(points_2, layer=(1, 0))
    
    # Bottom ribbon - sinusoidal wave with gradual width increase
    y_center_3 = -0.55
    amplitude_3 = 0.06
    wavelength_3 = 7.5
    phase_3 = np.pi  # Out of phase with top
    
    # Width gradually increases from left to right
    width_3 = 0.10 + 0.08 * (x / length) ** 2
    
    y_wave_3 = y_center_3 + amplitude_3 * np.sin(2 * np.pi * x / wavelength_3 + phase_3)
    y_top_3 = y_wave_3 + width_3 / 2
    y_bot_3 = y_wave_3 - width_3 / 2
    
    points_3 = list(zip(x, y_top_3)) + list(zip(x[::-1], y_bot_3[::-1]))
    c.add_polygon(points_3, layer=(1, 0))
    
    return c

# Create the component
device = wavy_ribbons()

# Save to GDS
device.write_gds("wavy_ribbons.gds")

# Optional: show the device
device.show()