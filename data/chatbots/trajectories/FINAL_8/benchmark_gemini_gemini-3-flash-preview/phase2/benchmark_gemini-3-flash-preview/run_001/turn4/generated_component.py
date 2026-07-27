import gdsfactory as gf

@gf.cell
def recreated_device_v5():
    """
    Robust recreation of the photonic device.
    Footprint: 120um x 4um.
    
    Fix: Manual path construction replaces gf.path.smooth to avoid 
    radius/distance errors in tight vertical spaces.
    """
    c = gf.Component()
    
    # --- Dimensions ---
    w_total = 120.0
    h_total = 4.0
    hw = w_total / 2  # 60.0
    hh = h_total / 2  # 2.0
    layer = (1, 0)
    
    # --- 1. Central Group: 5 Straight Waveguides ---
    # Centered vertically around y=0
    w_thin = 0.08
    y_center = [-0.3, -0.15, 0.0, 0.15, 0.3]
    xs_thin = gf.cross_section.cross_section(width=w_thin, layer=layer)
    
    for y in y_center:
        s = c << gf.components.straight(length=w_total, cross_section=xs_thin)
        s.movey(y)
        s.movex(-hw)
        
    # --- 2. U-Shape (Staple) Construction ---
    # Radius must be smaller than the shortest leg (2.0 - 1.9 = 0.1)
    radius = 0.05
    
    # Nested U-shape parameters (Innermost thick, then 4 thin)
    y_horizontals = [0.8, 1.3, 1.5, 1.7, 1.9] # Y-position of the flat part
    widths = [0.8, 0.08, 0.08, 0.08, 0.08]     # Innermost is much thicker
    x_half_spans = [50.0, 53.0, 55.5, 57.5, 59.5] # Horizontal reach
    
    def add_u_group(sign=1):
        """Adds a group of 5 nested staples. sign=1 for top, -1 for bottom."""
        for y_h, w, x_h in zip(y_horizontals, widths, x_half_spans):
            # Calculate lengths for a manual path
            # vertical_leg + bend + horizontal_span + bend + vertical_leg
            leg_len = (hh - y_h) - radius
            span_len = (2 * x_h) - (2 * radius)
            
            p = gf.Path()
            p.append(gf.path.straight(length=leg_len))
            p.append(gf.path.euler(radius=radius, angle=-90))
            p.append(gf.path.straight(length=span_len))
            p.append(gf.path.euler(radius=radius, angle=-90))
            p.append(gf.path.straight(length=leg_len))
            
            xs = gf.cross_section.cross_section(width=w, layer=layer)
            staple = c << gf.path.extrude(p, cross_section=xs)
            
            # Position the staple
            if sign == 1:
                # Top group: Starts at y=2.0, goes down, then back up to y=2.0
                staple.rotate(180)
                staple.movey(hh)
                staple.movex(x_h)
            else:
                # Bottom group: Starts at y=-2.0, goes up, then back down to y=-2.0
                staple.movey(-hh)
                staple.movex(-x_h)

    # Add both groups
    add_u_group(sign=1)  # Top
    add_u_group(sign=-1) # Bottom

    return c

if __name__ == "__main__":
    device = recreated_device_v5()
    device.write_gds("recreated_device_v5.gds")
    device.show()