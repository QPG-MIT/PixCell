import gdsfactory as gf
import numpy as np

@gf.cell
def fiber_coupler_device():
    c = gf.Component()
    
    # Dimensions from footprint
    total_length = 18.24
    total_height = 0.7
    layer = (1, 0)
    
    # Component parameters
    wg_width = 0.06
    curve_radius = 0.15
    grating_length = 7.5
    grating_start = 3.0
    grating_period = 0.1
    grating_duty = 0.5
    taper_length = 7.0
    taper_start = grating_start + grating_length
    
    # Vertical offset for top and bottom structures
    y_offset = 0.25
    
    # Helper function to create a curved section using polygon
    def create_curve(radius, width, angle_deg, flip=False):
        npoints = 50
        angles = np.linspace(0, np.radians(angle_deg), npoints)
        
        # Inner curve
        x_inner = radius * np.cos(angles)
        y_inner = radius * np.sin(angles)
        
        # Outer curve
        outer_radius = radius + width
        x_outer = outer_radius * np.cos(angles)
        y_outer = outer_radius * np.sin(angles)
        
        # Create closed polygon
        points = []
        for i in range(npoints):
            points.append((x_inner[i], y_inner[i]))
        for i in range(npoints-1, -1, -1):
            points.append((x_outer[i], y_outer[i]))
        
        poly = gf.Component()
        poly.add_polygon(points, layer=layer)
        return poly
    
    # Create top structure
    # 1. Curved section (left) - top
    curve_top = c << create_curve(curve_radius, wg_width, 90)
    curve_top.rotate(180)
    curve_top.move((1.0, y_offset + curve_radius))
    
    # 2. Solid section connecting curve to grating
    solid_top = c << gf.components.rectangle(
        size=(grating_start - 1.0, wg_width),
        layer=layer,
        centered=False
    )
    solid_top.move((1.0, y_offset - wg_width/2))
    
    # 3. Grating section (middle) - top
    num_bars = int(grating_length / grating_period)
    for i in range(num_bars):
        x_pos = grating_start + i * grating_period
        bar = c << gf.components.rectangle(
            size=(grating_period * grating_duty, wg_width),
            layer=layer,
            centered=False
        )
        bar.move((x_pos, y_offset - wg_width/2))
    
    # 4. Taper section (right) - top
    # Create taper using polygon
    taper_points = [
        (taper_start, y_offset - wg_width/2),
        (taper_start + taper_length, y_offset),
        (taper_start, y_offset + wg_width/2)
    ]
    c.add_polygon(taper_points, layer=layer)
    
    # Create bottom structure (mirrored)
    # 1. Curved section (left) - bottom
    curve_bottom = c << create_curve(curve_radius, wg_width, 90)
    curve_bottom.rotate(0)
    curve_bottom.move((1.0, -y_offset - curve_radius - wg_width))
    
    # 2. Solid section connecting curve to grating
    solid_bottom = c << gf.components.rectangle(
        size=(grating_start - 1.0, wg_width),
        layer=layer,
        centered=False
    )
    solid_bottom.move((1.0, -y_offset - wg_width/2))
    
    # 3. Grating section (middle) - bottom
    for i in range(num_bars):
        x_pos = grating_start + i * grating_period
        bar = c << gf.components.rectangle(
            size=(grating_period * grating_duty, wg_width),
            layer=layer,
            centered=False
        )
        bar.move((x_pos, -y_offset - wg_width/2))
    
    # 4. Taper section (right) - bottom
    taper_points_bottom = [
        (taper_start, -y_offset - wg_width/2),
        (taper_start + taper_length, -y_offset),
        (taper_start, -y_offset + wg_width/2)
    ]
    c.add_polygon(taper_points_bottom, layer=layer)
    
    # 5. Center connecting line
    center_line = c << gf.components.rectangle(
        size=(grating_length + 2.0, 0.02),
        layer=layer,
        centered=True
    )
    center_line.move((grating_start + grating_length/2, 0))
    
    return c

# Create the device
device = fiber_coupler_device()

# Save to GDS
device.write_gds("fiber_coupler_device.gds")

# Optional: show the device
device.show()