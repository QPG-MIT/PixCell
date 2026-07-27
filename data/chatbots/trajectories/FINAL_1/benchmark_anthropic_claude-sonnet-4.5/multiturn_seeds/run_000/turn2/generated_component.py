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
    wg_width = 0.15  # Base waveguide width
    bulge_start = 27.0  # Where bulge begins
    bulge_height = 0.35  # Maximum bulge extension
    
    # Vertical positions (spacing to fill 1.7 μm height)
    top_y = 0.7
    mid_y = 0.0
    bot_y = -0.7
    
    # Create top waveguide with upward bulge
    x_bulge = np.linspace(bulge_start, total_length, 80)
    # Smooth bulge profile - starts at 0, peaks in middle, returns to base
    bulge_progress = (x_bulge - bulge_start) / (total_length - bulge_start)
    bulge_profile_top = bulge_height * np.sin(np.pi * bulge_progress) * np.sin(np.pi * bulge_progress * 0.5)
    
    top_points = []
    # Left straight section - top edge
    top_points.append((0, top_y + wg_width/2))
    top_points.append((bulge_start, top_y + wg_width/2))
    # Bulge section - top edge (expands upward)
    for i, x in enumerate(x_bulge):
        top_points.append((x, top_y + wg_width/2 + bulge_profile_top[i]))
    # Right to left - bottom edge (stays relatively flat)
    top_points.append((total_length, top_y - wg_width/2))
    top_points.append((bulge_start, top_y - wg_width/2))
    top_points.append((0, top_y - wg_width/2))
    
    c.add_polygon(top_points, layer=layer)
    
    # Create middle waveguide (straight, constant width)
    mid_points = [
        (0, mid_y + wg_width/2),
        (total_length, mid_y + wg_width/2),
        (total_length, mid_y - wg_width/2),
        (0, mid_y - wg_width/2)
    ]
    c.add_polygon(mid_points, layer=layer)
    
    # Create bottom waveguide with downward bulge
    # Bulge profile for bottom (mirror of top)
    bulge_profile_bot = bulge_height * np.sin(np.pi * bulge_progress) * np.sin(np.pi * bulge_progress * 0.5)
    
    bot_points = []
    # Left straight section - top edge
    bot_points.append((0, bot_y + wg_width/2))
    bot_points.append((bulge_start, bot_y + wg_width/2))
    # Straight through bulge region for top edge
    bot_points.append((total_length, bot_y + wg_width/2))
    # Right to left - bottom edge with downward bulge
    for i, x in enumerate(reversed(x_bulge)):
        idx = len(x_bulge) - 1 - i
        bot_points.append((x, bot_y - wg_width/2 - bulge_profile_bot[idx]))
    bot_points.append((bulge_start, bot_y - wg_width/2))
    bot_points.append((0, bot_y - wg_width/2))
    
    c.add_polygon(bot_points, layer=layer)
    
    return c

# Create and save the device
device = device_from_image()
device.write_gds("device_from_image.gds")
print(f"Device created with bounding box: {device.bbox}")
print(f"Device size: {device.dxsize:.2f} x {device.dysize:.2f} μm")