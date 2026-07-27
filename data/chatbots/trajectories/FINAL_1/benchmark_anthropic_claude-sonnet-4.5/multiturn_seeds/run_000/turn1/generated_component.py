import gdsfactory as gf
import numpy as np

@gf.cell
def device_from_image():
    """
    Recreates the three-waveguide device with curved bulges.
    Total footprint: 40.0 μm × 1.7 μm
    """
    c = gf.Component()
    
    # Parameters
    total_length = 40.0
    layer = (1, 0)
    
    # Waveguide dimensions
    wg_width = 0.25  # Initial narrow width
    straight_len = 28.0  # Length before bulge starts
    bulge_start = 28.0
    
    # Vertical positions (centered around 0)
    top_y = 0.6
    mid_y = 0.0
    bot_y = -0.6
    
    # Create top waveguide with upward bulge
    # Use smooth curved profile for bulge
    x_bulge = np.linspace(bulge_start, total_length, 50)
    bulge_profile = 0.15 * np.sin(np.pi * (x_bulge - bulge_start) / (total_length - bulge_start))
    
    top_points = []
    # Left straight section - top edge
    top_points.append((0, top_y + wg_width/2))
    top_points.append((straight_len, top_y + wg_width/2))
    # Bulge section - top edge
    for i, x in enumerate(x_bulge):
        top_points.append((x, top_y + wg_width/2 + bulge_profile[i]))
    # Right to left - bottom edge
    for i, x in enumerate(reversed(x_bulge)):
        top_points.append((x, top_y - wg_width/2))
    top_points.append((straight_len, top_y - wg_width/2))
    top_points.append((0, top_y - wg_width/2))
    
    c.add_polygon(top_points, layer=layer)
    
    # Create middle waveguide (straight/tapered)
    mid_points = [
        (0, mid_y + wg_width/2),
        (total_length, mid_y + wg_width/2),
        (total_length, mid_y - wg_width/2),
        (0, mid_y - wg_width/2)
    ]
    c.add_polygon(mid_points, layer=layer)
    
    # Create bottom waveguide with downward bulge
    bot_points = []
    # Left straight section - top edge
    bot_points.append((0, bot_y + wg_width/2))
    bot_points.append((straight_len, bot_y + wg_width/2))
    # Transition through straight for top edge
    for i, x in enumerate(x_bulge):
        bot_points.append((x, bot_y + wg_width/2))
    # Right to left - bottom edge with bulge
    for i, x in enumerate(reversed(x_bulge)):
        idx = len(x_bulge) - 1 - i
        bot_points.append((x, bot_y - wg_width/2 - bulge_profile[idx]))
    bot_points.append((straight_len, bot_y - wg_width/2))
    bot_points.append((0, bot_y - wg_width/2))
    
    c.add_polygon(bot_points, layer=layer)
    
    return c

# Create and save the device
device = device_from_image()
device.write_gds("device_from_image.gds")
print(f"Device created with footprint: {device.bbox}")