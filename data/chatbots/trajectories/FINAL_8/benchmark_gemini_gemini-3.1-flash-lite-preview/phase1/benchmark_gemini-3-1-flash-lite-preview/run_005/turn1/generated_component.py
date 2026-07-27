import gdsfactory as gf
import numpy as np

@gf.cell
def custom_grating_device():
    """
    Creates a grating-like structure with curved vertical profiles 
    by composing parametric rectangle primitives.
    """
    c = gf.Component()
    
    # 1. Define Geometry Parameters
    # Footprint constraints from prompt: [120um, 4um]
    total_width = 120.0
    total_height = 4.0
    num_bars = 15  # Total number of horizontal elements
    
    # Define vertical positions for the bars
    y_coords = np.linspace(-total_height / 2, total_height / 2, num_bars)
    
    # Calculate uniform height for bars (with small gap)
    bar_height = (total_height / num_bars) * 0.7
    
    # 2. Composition Logic
    for y in y_coords:
        # Calculate width to create the curve (parabolic profile)
        # We want the width to be smallest at y=0 (middle) and largest at y=top/bottom
        # Normalize y to [-1, 1]
        y_norm = (y / (total_height / 2))
        
        # Curve function: width = min_width + (max_width - min_width) * y^2
        # We set min_width to 0.5 of total_width
        min_width = total_width * 0.6
        max_width = total_width
        current_width = min_width + (max_width - min_width) * (y_norm ** 2)
        
        # Create the rectangular primitive
        rect = c << gf.components.rectangle(
            size=(current_width, bar_height), 
            layer=(1, 0), 
            centered=True
        )
        
        # Position the primitive
        rect.movey(y)
        
    return c

# 3. Create, Visualize, and Save
# Instantiate the component
device = custom_grating_device()

# Save the GDS file
device.write_gds("custom_grating.gds")

# Preview
device.show()