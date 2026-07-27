import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_ribbons():
    """Create three wavy ribbons with varying widths."""
    c = gf.Component()
    
    # Parameters
    length = 40.0
    total_height = 1.7
    n_points = 300
    
    x = np.linspace(0, length, n_points)
    
    # Top ribbon - tapers wider in the middle-right section
    y_center_1 = 0.57
    # Width variation: starts narrow, expands in middle-right
    width_1 = 0.08 + 0.12 * (1 / (1 + np.exp(-0.3 * (x - 25))))
    # Add waviness to edges
    wave_1 = 0.04 * np.sin(2 * np.pi * x / 8)
    y_top_1 = y_center_1 + wave_1 + width_1 / 2
    y_bot_1 = y_center_1 + wave_1 - width_1 / 2
    
    # Create polygon
    points_top = list(zip(x, y_top_1))
    points_bot = list(zip(x[::-1], y_bot_1[::-1]))
    polygon_1 = points_top + points_bot
    c.add_polygon(polygon_1, layer=(1, 0))
    
    # Middle ribbon - more uniform width with slight taper
    y_center_2 = 0.0
    width_2 = 0.14 + 0.03 * np.sin(np.pi * x / length)
    y_top_2 = y_center_2 + width_2 / 2
    y_bot_2 = y_center_2 - width_2 / 2
    
    points_top = list(zip(x, y_top_2))
    points_bot = list(zip(x[::-1], y_bot_2[::-1]))
    polygon_2 = points_top + points_bot
    c.add_polygon(polygon_2, layer=(1, 0))
    
    # Bottom ribbon - starts narrow, gets significantly wider toward right
    y_center_3 = -0.57
    # Width increases gradually then more rapidly
    width_3 = 0.08 + 0.18 * (x / length) ** 1.5
    # Add gentle waviness
    wave_3 = 0.03 * np.sin(2 * np.pi * x / 12 + np.pi/4)
    y_top_3 = y_center_3 + wave_3 + width_3 / 2
    y_bot_3 = y_center_3 + wave_3 - width_3 / 2
    
    points_top = list(zip(x, y_top_3))
    points_bot = list(zip(x[::-1], y_bot_3[::-1]))
    polygon_3 = points_top + points_bot
    c.add_polygon(polygon_3, layer=(1, 0))
    
    return c

# Create the component
device = wavy_ribbons()

# Save to GDS
device.write_gds("wavy_ribbons.gds")

# Optional: show the device
device.show()