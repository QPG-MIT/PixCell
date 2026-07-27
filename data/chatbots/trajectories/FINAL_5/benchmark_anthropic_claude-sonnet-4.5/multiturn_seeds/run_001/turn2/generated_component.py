import gdsfactory as gf

@gf.cell
def grating_taper_coupler():
    """Recreate the tapered grating coupler device from the image"""
    c = gf.Component()
    
    # Parameters based on footprint [18.24, 0.7]
    total_length = 18.24
    
    # Structure dimensions
    structure_height = 0.17
    gap_between = 0.36
    
    # Section lengths
    solid_length = 3.5
    grating_length = 10.0
    taper_length = 4.74  # remaining: 18.24 - 3.5 - 10.0
    
    # Grating parameters
    num_teeth = 50
    tooth_width = grating_length / (num_teeth * 2)  # alternating teeth and gaps
    gap_width = tooth_width
    
    layer = (1, 0)
    
    # Y positions
    y_top = gap_between / 2
    y_bottom = -gap_between / 2 - structure_height
    
    # ===== TOP STRUCTURE =====
    # 1. Left solid block
    top_left = c << gf.components.rectangle(
        size=(solid_length, structure_height),
        layer=layer
    )
    top_left.move((0, y_top))
    
    # 2. Middle grating teeth (vertical bars)
    x_grating_start = solid_length
    for i in range(num_teeth):
        x_tooth = x_grating_start + i * (tooth_width + gap_width)
        tooth = c << gf.components.rectangle(
            size=(tooth_width, structure_height),
            layer=layer
        )
        tooth.move((x_tooth, y_top))
    
    # 3. Right taper (triangle pointing right)
    x_taper_start = x_grating_start + grating_length
    taper_pts = [
        (x_taper_start, y_top),
        (x_taper_start, y_top + structure_height),
        (total_length, y_top + structure_height / 2)
    ]
    c.add_polygon(taper_pts, layer=layer)
    
    # ===== BOTTOM STRUCTURE (mirrored) =====
    # 1. Left taper (triangle pointing left)
    bottom_taper_pts = [
        (0, y_bottom + structure_height / 2),
        (taper_length, y_bottom),
        (taper_length, y_bottom + structure_height)
    ]
    c.add_polygon(bottom_taper_pts, layer=layer)
    
    # 2. Middle grating teeth
    x_grating_start_bottom = taper_length
    for i in range(num_teeth):
        x_tooth = x_grating_start_bottom + i * (tooth_width + gap_width)
        tooth = c << gf.components.rectangle(
            size=(tooth_width, structure_height),
            layer=layer
        )
        tooth.move((x_tooth, y_bottom))
    
    # 3. Right solid block
    x_solid_start = x_grating_start_bottom + grating_length
    bottom_right = c << gf.components.rectangle(
        size=(total_length - x_solid_start, structure_height),
        layer=layer
    )
    bottom_right.move((x_solid_start, y_bottom))
    
    # ===== CONNECTING BAR =====
    bar_length = 9.6
    bar_height = 0.02
    bar_x_start = 3.2
    
    center_bar = c << gf.components.rectangle(
        size=(bar_length, bar_height),
        layer=layer
    )
    center_bar.move((bar_x_start, -bar_height / 2))
    
    return c

# Create the device
device = grating_taper_coupler()

# Save to GDS
device.write_gds("grating_taper_coupler.gds")

# Optional: show the device
device.show()