import gdsfactory as gf

@gf.cell
def recreated_device():
    c = gf.Component()
    
    # Device dimensions from constraint
    total_width = 40.0
    total_height = 1.7
    
    # Waveguide parameters
    wg_thin = 0.22  # thin waveguide width
    wg_bulge = 0.65  # bulge width
    wg_taper_end = 0.9  # end taper width
    
    # Vertical positions (stacked within 1.7 um height)
    y_top = 0.6
    y_mid = 0.0
    y_bottom = -0.55
    
    # TOP WAVEGUIDE - with bulge in middle-right section
    # Left thin section
    top_left = c << gf.components.rectangle(size=(18, wg_thin), layer=(1, 0))
    top_left.xmin = 0
    top_left.y = y_top
    
    # Bulge section
    top_bulge = c << gf.components.rectangle(size=(14, wg_bulge), layer=(1, 0))
    top_bulge.xmin = 18
    top_bulge.y = y_top
    
    # Right thin section
    top_right = c << gf.components.rectangle(size=(8, wg_thin), layer=(1, 0))
    top_right.xmin = 32
    top_right.y = y_top
    
    # MIDDLE WAVEGUIDE - angled/diagonal
    path_mid = gf.Path()
    path_mid.append(gf.path.straight(length=36))
    xs_mid = gf.cross_section.cross_section(width=wg_thin, layer=(1, 0))
    mid_wg = c << path_mid.extrude(xs_mid)
    # Rotate slightly to create diagonal appearance
    mid_wg.rotate(2.5, center=(0, y_mid))
    mid_wg.xmin = 0
    mid_wg.y = y_mid
    
    # BOTTOM WAVEGUIDE - thin with taper at right end
    # Thin section
    bottom_straight = c << gf.components.rectangle(size=(27, wg_thin), layer=(1, 0))
    bottom_straight.xmin = 0
    bottom_straight.y = y_bottom
    
    # Taper section at end
    bottom_taper = c << gf.components.taper(
        length=13,
        width1=wg_thin,
        width2=wg_taper_end,
        layer=(1, 0)
    )
    bottom_taper.xmin = 27
    bottom_taper.y = y_bottom
    
    # Flatten to resolve off-grid instances from rotation
    c.flatten()
    
    return c

# Create and save the device
device = recreated_device()
device.show()  # Optional: display in viewer
device.write_gds("device.gds")