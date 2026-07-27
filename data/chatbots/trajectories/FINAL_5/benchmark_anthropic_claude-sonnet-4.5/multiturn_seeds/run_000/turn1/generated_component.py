import gdsfactory as gf
import numpy as np

@gf.cell
def fiber_coupler_device():
    c = gf.Component()
    
    # Overall dimensions from footprint
    total_length = 18.24
    total_height = 0.7
    
    # Structure parameters
    wg_width = 0.05
    tip_width = 0.01
    
    # Grating parameters
    grating_period = 0.13
    num_teeth = 60
    tooth_width = 0.055
    gap_width = grating_period - tooth_width
    tooth_height = 0.12
    
    # Section lengths
    curve_length = 3.0
    grating_length = num_teeth * grating_period
    taper_length = total_length - curve_length - grating_length
    
    # Vertical positions
    y_offset = 0.15
    
    # TOP STRUCTURE
    # Curved section (left) - create using polygon
    curve_points_top = []
    num_points = 50
    radius = 8.0
    angle_range = np.radians(20)
    for i in range(num_points):
        t = i / (num_points - 1)
        angle = np.pi + t * angle_range
        x = radius * np.cos(angle) + radius
        y = radius * np.sin(angle) + y_offset
        curve_points_top.append((x, y + wg_width/2))
    
    for i in range(num_points-1, -1, -1):
        t = i / (num_points - 1)
        angle = np.pi + t * angle_range
        x = radius * np.cos(angle) + radius
        y = radius * np.sin(angle) + y_offset
        curve_points_top.append((x, y - wg_width/2))
    
    c.add_polygon(curve_points_top, layer=(1, 0))
    
    # Grating section (middle top) - using polygons
    grating_start_x = curve_length
    for i in range(num_teeth):
        x_pos = grating_start_x + i * grating_period
        tooth_points = [
            (x_pos, y_offset - (wg_width + tooth_height)/2),
            (x_pos + tooth_width, y_offset - (wg_width + tooth_height)/2),
            (x_pos + tooth_width, y_offset + (wg_width + tooth_height)/2),
            (x_pos, y_offset + (wg_width + tooth_height)/2),
        ]
        c.add_polygon(tooth_points, layer=(1, 0))
    
    # Tapered section (right top)
    top_taper_start = curve_length + grating_length
    top_taper_points = [
        (top_taper_start, y_offset - wg_width/2),
        (top_taper_start, y_offset + wg_width/2),
        (total_length, y_offset + tip_width/2),
        (total_length, y_offset - tip_width/2),
    ]
    c.add_polygon(top_taper_points, layer=(1, 0))
    
    # MIDDLE LINE
    middle_line_points = [
        (curve_length - 0.2, -0.01),
        (curve_length + grating_length + 0.3, -0.01),
        (curve_length + grating_length + 0.3, 0.01),
        (curve_length - 0.2, 0.01),
    ]
    c.add_polygon(middle_line_points, layer=(1, 0))
    
    # BOTTOM STRUCTURE
    y_offset_bottom = -y_offset
    
    # Tapered section (left bottom)
    bottom_taper_points = [
        (0, y_offset_bottom - tip_width/2),
        (0, y_offset_bottom + tip_width/2),
        (curve_length, y_offset_bottom + wg_width/2),
        (curve_length, y_offset_bottom - wg_width/2),
    ]
    c.add_polygon(bottom_taper_points, layer=(1, 0))
    
    # Grating section (middle bottom) - using polygons
    for i in range(num_teeth):
        x_pos = grating_start_x + i * grating_period
        tooth_points = [
            (x_pos, y_offset_bottom - (wg_width + tooth_height)/2),
            (x_pos + tooth_width, y_offset_bottom - (wg_width + tooth_height)/2),
            (x_pos + tooth_width, y_offset_bottom + (wg_width + tooth_height)/2),
            (x_pos, y_offset_bottom + (wg_width + tooth_height)/2),
        ]
        c.add_polygon(tooth_points, layer=(1, 0))
    
    # Curved section (right bottom) - create using polygon
    curve_points_bottom = []
    for i in range(num_points):
        t = i / (num_points - 1)
        angle = -t * angle_range
        x = radius * np.cos(angle) + (total_length - curve_length - radius)
        y = radius * np.sin(angle) + y_offset_bottom
        curve_points_bottom.append((x, y + wg_width/2))
    
    for i in range(num_points-1, -1, -1):
        t = i / (num_points - 1)
        angle = -t * angle_range
        x = radius * np.cos(angle) + (total_length - curve_length - radius)
        y = radius * np.sin(angle) + y_offset_bottom
        curve_points_bottom.append((x, y - wg_width/2))
    
    c.add_polygon(curve_points_bottom, layer=(1, 0))
    
    # Center the component
    c.center()
    
    return c

# Generate the device
if __name__ == "__main__":
    device = fiber_coupler_device()
    device.show()
    device.write_gds("fiber_coupler_device.gds")
    print("GDS file generated: fiber_coupler_device.gds")