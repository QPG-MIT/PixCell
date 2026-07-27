import gdsfactory as gf
import numpy as np

@gf.cell
def grating_taper_coupler():
    """Recreate the tapered grating coupler device from the image"""
    c = gf.Component()
    
    # Parameters based on footprint
    total_length = 18.24
    total_height = 0.7
    
    # Individual structure parameters
    structure_height = 0.25
    gap = 0.2
    taper_length_side = 3.5
    grating_length = 11.0
    hook_length = 0.5
    
    # Grating parameters
    num_gratings = 60
    grating_width = grating_length / num_gratings
    duty_cycle = 0.5
    
    layer = (1, 0)
    
    # Create top structure using polygons
    # Top structure: hook on left, grating middle, taper to point on right
    
    # Top taper body (solid base before grating cuts)
    y_top = gap/2
    
    # Left hook curve
    hook_pts = []
    for i in np.linspace(0, np.pi, 20):
        x = hook_length * (1 - np.cos(i))
        y = y_top + structure_height/2 + structure_height/2 * np.sin(i)
        hook_pts.append((x, y))
    
    # Top edge of grating section
    x_grating_start = hook_length + taper_length_side
    for i in range(num_gratings):
        x_start = x_grating_start + i * grating_width
        x_end = x_start + grating_width * duty_cycle
        if i == 0:
            pts_top = [(hook_length, y_top + structure_height)]
        pts_top = [(x_start, y_top + structure_height), (x_end, y_top + structure_height)]
    
    # Right taper point
    x_end = total_length
    taper_pts = [
        (x_grating_start + grating_length, y_top + structure_height),
        (x_end, y_top + structure_height/2),
        (x_grating_start + grating_length, y_top)
    ]
    
    # Create top structure with grating
    x_offset = 0
    for i in range(num_gratings):
        x_bar = x_grating_start + i * grating_width
        bar_width = grating_width * duty_cycle
        if i % 2 == 0:  # Create grating by alternating bars
            bar = c.add_ref(gf.components.rectangle(
                size=(bar_width, structure_height),
                layer=layer
            ))
            bar.move((x_bar, y_top))
    
    # Add solid sections (hook, tapers)
    # Left curved section
    left_section = c.add_ref(gf.components.rectangle(
        size=(x_grating_start, structure_height),
        layer=layer
    ))
    left_section.move((0, y_top))
    
    # Right taper using polygon
    taper_right_pts = [
        (x_grating_start + grating_length, y_top),
        (x_end, y_top + structure_height/2),
        (x_grating_start + grating_length, y_top + structure_height)
    ]
    c.add_polygon(taper_right_pts, layer=layer)
    
    # Bottom structure (mirrored configuration)
    y_bottom = -gap/2
    
    # Left taper point for bottom
    taper_left_pts = [
        (0, y_bottom - structure_height/2),
        (taper_length_side, y_bottom),
        (taper_length_side, y_bottom - structure_height)
    ]
    c.add_polygon(taper_left_pts, layer=layer)
    
    # Grating section for bottom
    for i in range(num_gratings):
        x_bar = taper_length_side + i * grating_width
        bar_width = grating_width * duty_cycle
        if i % 2 == 0:
            bar = c.add_ref(gf.components.rectangle(
                size=(bar_width, structure_height),
                layer=layer
            ))
            bar.move((x_bar, y_bottom - structure_height))
    
    # Right solid section for bottom
    right_section = c.add_ref(gf.components.rectangle(
        size=(total_length - taper_length_side - grating_length, structure_height),
        layer=layer
    ))
    right_section.move((taper_length_side + grating_length, y_bottom - structure_height))
    
    # Horizontal connecting bar in the middle
    bar_length = 11.5
    bar_width = 0.02
    center_bar = c.add_ref(gf.components.rectangle(
        size=(bar_length, bar_width),
        layer=layer
    ))
    center_bar.move((3.5, -bar_width/2))
    
    return c

# Create the device
device = grating_taper_coupler()

# Save to GDS
device.write_gds("grating_taper_coupler.gds")

# Optional: show the device
device.show()