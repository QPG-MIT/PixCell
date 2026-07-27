import gdsfactory as gf

@gf.cell
def recreated_device():
    c = gf.Component()
    
    # Device dimensions from constraint
    total_width = 40.0
    total_height = 1.7
    
    # Waveguide parameters
    wg_thin = 0.20  # thin waveguide width
    wg_bulge = 0.55  # bulge width for top waveguide
    wg_bottom_wide = 1.1  # wide end of bottom waveguide
    
    # Vertical positions (stacked within 1.7 um height)
    y_top = 0.55
    y_mid = 0.0
    y_bottom = -0.60
    
    # TOP WAVEGUIDE - smooth bulge with tapers
    # Left thin section
    top_left = c << gf.components.rectangle(size=(22, wg_thin), layer=(1, 0))
    top_left.xmin = 0
    top_left.y = y_top
    
    # Taper up to bulge
    top_taper_up = c << gf.components.taper(
        length=4,
        width1=wg_thin,
        width2=wg_bulge,
        layer=(1, 0)
    )
    top_taper_up.xmin = 22
    top_taper_up.y = y_top
    
    # Bulge section
    top_bulge = c << gf.components.rectangle(size=(6, wg_bulge), layer=(1, 0))
    top_bulge.xmin = 26
    top_bulge.y = y_top
    
    # Taper down from bulge
    top_taper_down = c << gf.components.taper(
        length=4,
        width1=wg_bulge,
        width2=wg_thin,
        layer=(1, 0)
    )
    top_taper_down.xmin = 32
    top_taper_down.y = y_top
    
    # Right thin section
    top_right = c << gf.components.rectangle(size=(4, wg_thin), layer=(1, 0))
    top_right.xmin = 36
    top_right.y = y_top
    
    # MIDDLE WAVEGUIDE - straight and thin
    mid_wg = c << gf.components.rectangle(size=(36, wg_thin), layer=(1, 0))
    mid_wg.xmin = 0
    mid_wg.y = y_mid
    
    # BOTTOM WAVEGUIDE - thin with large taper at right end
    # Thin section
    bottom_straight = c << gf.components.rectangle(size=(23, wg_thin), layer=(1, 0))
    bottom_straight.xmin = 0
    bottom_straight.y = y_bottom
    
    # Large taper section at end
    bottom_taper = c << gf.components.taper(
        length=17,
        width1=wg_thin,
        width2=wg_bottom_wide,
        layer=(1, 0)
    )
    bottom_taper.xmin = 23
    bottom_taper.y = y_bottom
    
    return c

# Create and save the device
device = recreated_device()
device.show()  # Optional: display in viewer
device.write_gds("device.gds")