import gdsfactory as gf
import numpy as np

@gf.cell
def mirrored_hourglass_grating():
    """
    Creates two mirrored sections of stacked bars with an hourglass (concave)
    profile, separated by a central gap.
    """
    c = gf.Component()
    
    # 1. Define Geometry Parameters
    total_height = 4.0
    total_width = 120.0
    gap = 0.5            # Space in the middle
    num_bars_per_side = 8
    
    # Define vertical start/end for the top half
    y_start = gap / 2
    y_end = total_height / 2
    y_coords = np.linspace(y_start, y_end, num_bars_per_side)
    
    # Determine bar height based on available space
    # (Leaving a small vertical spacing between bars)
    available_height = (y_end - y_start)
    bar_height = (available_height / num_bars_per_side) * 0.6
    
    # 2. Composition Logic
    # Min width is at the gap (inner), Max width is at the outer edges
    min_width = total_width * 0.5
    max_width = total_width
    
    for y in y_coords:
        # Calculate normalized position [0, 1] relative to the half-section
        norm_y = (y - y_start) / (y_end - y_start)
        
        # Quadratic curve for the profile
        current_width = min_width + (max_width - min_width) * (norm_y ** 2)
        
        # Create Top Bar
        top_bar = c << gf.components.rectangle(
            size=(current_width, bar_height), 
            layer=(1, 0), 
            centered=True
        )
        top_bar.movey(y)
        
        # Create Bottom Bar (Mirrored)
        bot_bar = c << gf.components.rectangle(
            size=(current_width, bar_height), 
            layer=(1, 0), 
            centered=True
        )
        bot_bar.movey(-y)
        
    return c

# 3. Create and Save
device = mirrored_hourglass_grating()
device.write_gds("hourglass_grating.gds")
device.show()