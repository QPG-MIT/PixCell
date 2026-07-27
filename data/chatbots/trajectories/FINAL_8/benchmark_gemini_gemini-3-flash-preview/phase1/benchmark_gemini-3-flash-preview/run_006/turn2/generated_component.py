import gdsfactory as gf

@gf.cell
def recreated_device_geometry():
    """
    Recreates the device geometry from the image using parametric primitives.
    Uses gf.Path(points) to create the flared curves, avoiding the bezier attribute error.
    Footprint: 120.0 x 4.0 um.
    """
    c = gf.Component("recreated_device")
    layer = (1, 0)
    
    # --- Dimensions & Constants ---
    W_MAX = 120.0
    W_BLOCK_BASE = 88.0
    
    # Line widths and spacings
    w_thin = 0.08
    w_thick = 0.32
    pitch_center = 0.18
    pitch_block = 0.22
    y_gap = 0.5  # Gap between center grating and outer blocks
    
    # 1. CENTRAL SECTION (5 full-width thin lines)
    for i in range(-2, 3):
        line = c << gf.components.rectangle(size=(W_MAX, w_thin), layer=layer, centered=True)
        line.y = i * pitch_center

    # 2. TOP AND BOTTOM SYMMETRIC BLOCKS
    def add_block(is_top=True):
        y_sign = 1 if is_top else -1
        # Start coordinate for the block (the thick bar)
        y_start = y_sign * (2 * pitch_center + y_gap)
        
        # A. Thick Base Bar
        thick = c << gf.components.rectangle(size=(W_BLOCK_BASE, w_thick), layer=layer, centered=True)
        thick.y = y_start
        
        # B. 4 Thin Bars - widths increase to follow the flare of the rails
        flare_step = 4.2
        for i in range(1, 5):
            y_pos = y_start + y_sign * (w_thick/2 + i * pitch_block)
            current_w = W_BLOCK_BASE + (i * flare_step)
            thin = c << gf.components.rectangle(size=(current_w, w_thin), layer=layer, centered=True)
            thin.y = y_pos
            
        # C. Flared Side Rails (Dual-Rail)
        rail_w = 0.06
        rail_xs = gf.cross_section.cross_section(width=rail_w, layer=layer)
        y_end = y_start + y_sign * (w_thick/2 + 4.2 * pitch_block)
        
        # Helper function for Bezier points
        def get_bezier_pts(p0, p1, p2):
            return [
                ( (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0],
                  (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1] )
                for t in [j/20 for j in range(21)]
            ]

        for x_sign in [-1, 1]:
            # Control points for the flare path
            p0 = (x_sign * W_BLOCK_BASE / 2, y_start - y_sign * w_thick / 2)
            p2 = (x_sign * (W_BLOCK_BASE / 2 + 4 * flare_step / 2 + 1.2), y_end)
            p1 = (x_sign * (W_BLOCK_BASE / 2 + 0.4), (p0[1] + p2[1]) / 2)
            
            # Inner rail path
            inner_pts = get_bezier_pts(p0, p1, p2)
            c << gf.path.extrude(gf.Path(inner_pts), cross_section=rail_xs)
            
            # Outer rail path (shifted slightly)
            offset = x_sign * 0.18
            p0_o, p1_o, p2_o = (p0[0]+offset, p0[1]), (p1[0]+offset, p1[1]), (p2[0]+offset, p2[1])
            outer_pts = get_bezier_pts(p0_o, p1_o, p2_o)
            c << gf.path.extrude(gf.Path(outer_pts), cross_section=rail_xs)

    # Generate top and bottom blocks
    add_block(is_top=True)
    add_block(is_top=False)
    
    return c

if __name__ == "__main__":
    component = recreated_device_geometry()
    component.write_gds("recreated_device.gds")