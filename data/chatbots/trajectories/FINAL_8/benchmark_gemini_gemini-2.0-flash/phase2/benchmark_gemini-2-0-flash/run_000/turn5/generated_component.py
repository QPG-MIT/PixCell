import gdsfactory as gf
from gdsfactory.path import smooth
from gdsfactory.cross_section import strip
import numpy as np

@gf.cell
def create_device():
    c = gf.Component("optical_device")

    # Cross-section parameters
    width = 0.5
    xs = strip(width=width, layer=(1, 0))  # Simplify the cross-section

    # Parameters for the entire structure
    num_bars = 5
    bar_length = 100
    bar_spacing = 1
    vertical_length = 5

    # Define the points for the path
    points = []
    vertical_offset = (num_bars - 1) / 2 * bar_spacing + vertical_length/2

    # Start point
    x_start = -bar_length/2

    # Build the points for top and bottom sections
    points.append((x_start, vertical_offset))
    points.append((x_start, vertical_offset + vertical_length))
    points.append((bar_length/2, vertical_offset + vertical_length))
    points.append((bar_length/2, vertical_offset))
    
    points.append((bar_length/2, -vertical_offset))
    points.append((bar_length/2, -vertical_offset - vertical_length))
    points.append((x_start, -vertical_offset - vertical_length))
    points.append((x_start, -vertical_offset))

    #Points for the bars - Ensure a minimum spacing
    x_end = bar_length/2
    for i in range(num_bars):
        y_offset = (i - (num_bars - 1) / 2) * bar_spacing
        points.append((x_start, y_offset))
        points.append((x_end, y_offset))
    
    #Dedublicate the points to avoid issues with the smoothing function.
    points = np.unique(points, axis=0)
    
    # Create a path from the points
    path = smooth(points=points, radius=0.1)  # Round the corners - Reduced radius

    # Extrude the path
    device = path.extrude(cross_section=xs) # Convert path to component with constant width.

    c << device

    return c

device = create_device()
device.write_gds("optical_device.gds")
device.show()