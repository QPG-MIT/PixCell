import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreates the photonic device geometry from the provided image.
    Footprint: 120um x 4um.
    
    Fix: Reduced radius and adjusted y-spacing to satisfy path.smooth constraints.
    """
    c = gf.Component()
    
    # --- Dimensions ---
    width_total = 120.0
    height_total = 4.0
    layer = (1, 0)
    
    # Coordinates
    hw = width_total / 2.0
    hh = height_total / 2.0  # hh = 2.0
    
    # Indent for the U-shapes so they are visually contained within the boundary
    # The image shows vertical arms at the far left and right.
    u_hw = hw - 2.0 
    
    # Waveguide widths
    w_thin = 0.08
    w_thick = 0.4
    
    # Small radius for sharp-looking corners that fit within small vertical gaps
    r = 0.05 
    
    # --- 1. Central Group: 5 Straight Waveguides ---
    # These span the full width of the 120um footprint.
    center_y_positions = [-0.4, -0.2, 0.0, 0.2, 0.4]
    xs_thin = gf.cross_section.cross_section(width=w_thin, layer=layer)
    
    for y in center_y_positions:
        s = c << gf.components.straight(length=width_total, cross_section=xs_thin)
        s.movex(-hw)
        s.movey(y)
        
    # --- 2. Top and Bottom Nested Groups ---
    # Each group: 1 thick waveguide (inner) and 4 thin waveguides (outer).
    # Horizontal segment heights (y-coordinates). 
    # Must stay below hh=2.0 and have enough room for radius r.
    y_vals = [0.85, 1.15, 1.35, 1.55, 1.75]
    widths = [w_thick, w_thin, w_thin, w_thin, w_thin]
    
    for y_v, w in zip(y_vals, widths):
        xs = gf.cross_section.cross_section(width=w, layer=layer)
        
        # --- Top U-shape (Facing Up) ---
        # Waypoints: Top Boundary -> Down to Y-level -> Across -> Back to Top Boundary
        p_top = gf.path.smooth(
            points=[(-u_hw, hh), (-u_hw, y_v), (u_hw, y_v), (u_hw, hh)],
            radius=r
        )
        c << gf.path.extrude(p_top, cross_section=xs)
        
        # --- Bottom U-shape (Facing Down) ---
        # Mirror of the top path waypoints
        p_bot = gf.path.smooth(
            points=[(-u_hw, -hh), (-u_hw, -y_v), (u_hw, -y_v), (u_hw, -hh)],
            radius=r
        )
        c << gf.path.extrude(p_bot, cross_section=xs)
        
    return c

if __name__ == "__main__":
    # Generate the component
    device = recreated_device()
    
    # Save as GDS
    device.write_gds("recreated_device.gds")
    
    # Visualize
    device.show()