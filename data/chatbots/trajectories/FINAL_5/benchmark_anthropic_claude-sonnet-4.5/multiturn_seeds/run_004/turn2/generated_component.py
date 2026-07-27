import gdsfactory as gf
import numpy as np

@gf.cell
def fiber_coupler_device():
    c = gf.Component()
    
    # Dimensions from footprint
    total_length = 18.24
    total_height = 0.7
    layer = (1, 0)
    
    # Component parameters - adjusted for better match
    wg_width = 0.12
    curve_length = 1.2  # Horizontal extent of curve
    curve_height = 0.35  # Vertical extent of curve
    solid_length = 1.5
    grating_length = 6.5
    grating_start = curve_length + solid_length
    grating_period = 0.08
    grating_duty = 0.5
    taper_length = 8.5
    taper_start = grating_start + grating_length
    
    # Vertical offset for top and bottom structures
    y_offset = 0.19
    
    # Helper function to create a curved hook section
    def create_hook_curve(width, length, height, upward=True):
        npoints = 60
        t = np.linspace(0, 1, npoints)
        
        # Create smooth curve using cubic bezier-like profile
        x = length * t
        if upward:
            y = height * (1 - np.cos(np.pi * t)) / 2
        else:
            y = -height * (1 - np.cos(np.pi * t)) / 2
        
        # Create inner and outer curves
        points_inner = list(zip(x, y))
        points_outer = list(zip(x, y + width if upward else y - width))
        
        # Close the polygon
        points = [(0, 0)]
        points.extend(points_inner)
        if upward:
            points.append((length, height + width))
            points.extend(reversed(points_outer))
            points.append((0, width))
        else:
            points.append((length, -height - width))
            points.extend(reversed(points_outer))
            points.append((0, -width))
        
        poly = gf.Component()
        poly.add_polygon(points, layer=layer)
        return poly
    
    # Create top structure
    # 1. Curved hook section (left) - top
    curve_top = c << create_hook_curve(wg_width, curve_length, curve_height, upward=True)
    curve_top.move((0, y_offset - wg_width))
    
    # 2. Solid section connecting curve to grating - top
    solid_top = c << gf.components.rectangle(
        size=(solid_length, wg_width),
        layer=layer,
        centered=False
    )
    solid_top.move((curve_length, y_offset - wg_width/2))
    
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
    taper_points = [
        (taper_start, y_offset - wg_width/2),
        (taper_start + taper_length, y_offset),
        (taper_start, y_offset + wg_width/2)
    ]
    c.add_polygon(taper_points, layer=layer)
    
    # Create bottom structure (mirrored)
    # 1. Curved hook section (left) - bottom
    curve_bottom = c << create_hook_curve(wg_width, curve_length, curve_height, upward=False)
    curve_bottom.move((0, -y_offset + wg_width))
    
    # 2. Solid section connecting curve to grating - bottom
    solid_bottom = c << gf.components.rectangle(
        size=(solid_length, wg_width),
        layer=layer,
        centered=False
    )
    solid_bottom.move((curve_length, -y_offset - wg_width/2))
    
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
    
    # 5. Center connecting line (very thin)
    center_line = c << gf.components.rectangle(
        size=(grating_length + 1.0, 0.015),
        layer=layer,
        centered=True
    )
    center_line.move((grating_start + grating_length/2 - 0.5, 0))
    
    return c

# Create the device
device = fiber_coupler_device()

# Save to GDS
device.write_gds("fiber_coupler_device.gds")

# Optional: show the device
device.show()