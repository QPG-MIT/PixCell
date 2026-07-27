import gdsfactory as gf
import numpy as np

@gf.cell
def chain_link_device():
    c = gf.Component()
    layer = (1, 0)
    
    # Device parameters (5.5 x 3.0 μm footprint)
    W = 5.5
    H = 3.0
    ring_t = 0.25
    
    # Stadium geometry
    R = H / 2  # radius of semicircular ends
    S = W - H  # straight section length
    
    # Create stadium polygon using explicit points
    n = 64  # points per semicircle
    
    def make_stadium_points(radius, straight_len):
        pts = []
        # Right semicircle (bottom to top)
        for angle in np.linspace(-np.pi/2, np.pi/2, n):
            pts.append((straight_len/2 + radius * np.cos(angle), radius * np.sin(angle)))
        # Left semicircle (top to bottom)
        for angle in np.linspace(np.pi/2, 3*np.pi/2, n):
            pts.append((-straight_len/2 + radius * np.cos(angle), radius * np.sin(angle)))
        return pts
    
    # Outer stadium
    outer_pts = make_stadium_points(R, S)
    outer = gf.Component()
    outer.add_polygon(outer_pts, layer=layer)
    
    # Inner stadium
    inner_R = R - ring_t
    inner_pts = make_stadium_points(inner_R, S)
    inner = gf.Component()
    inner.add_polygon(inner_pts, layer=layer)
    
    # Create ring by subtraction
    ring = gf.boolean(outer, inner, operation="not", layer=layer)
    c << ring
    
    # ===== INTERNAL BARS =====
    bar_length = S + 2 * inner_R * 0.85  # extends into curved regions
    bar_h = 0.38
    frame_t = 0.08  # frame thickness around windows
    
    # Window dimensions
    win_h = bar_h - 2 * frame_t
    win_w = 0.50
    cell_spacing = win_w + frame_t * 2 + 0.08
    
    # ----- Top bar (3 windows) -----
    y_top = 0.48
    
    top_bar = gf.Component()
    top_bar.add_polygon([
        (-bar_length/2, y_top - bar_h/2),
        (bar_length/2, y_top - bar_h/2),
        (bar_length/2, y_top + bar_h/2),
        (-bar_length/2, y_top + bar_h/2)
    ], layer=layer)
    
    top_windows = gf.Component()
    for i in range(3):
        x = (i - 1) * cell_spacing
        top_windows.add_polygon([
            (x - win_w/2, y_top - win_h/2),
            (x + win_w/2, y_top - win_h/2),
            (x + win_w/2, y_top + win_h/2),
            (x - win_w/2, y_top + win_h/2)
        ], layer=layer)
    
    top_result = gf.boolean(top_bar, top_windows, operation="not", layer=layer)
    c << top_result
    
    # ----- Bottom bar (2 windows) -----
    y_bot = -0.48
    
    bot_bar = gf.Component()
    bot_bar.add_polygon([
        (-bar_length/2, y_bot - bar_h/2),
        (bar_length/2, y_bot - bar_h/2),
        (bar_length/2, y_bot + bar_h/2),
        (-bar_length/2, y_bot + bar_h/2)
    ], layer=layer)
    
    bot_windows = gf.Component()
    for i in range(2):
        x = (i - 0.5) * cell_spacing
        bot_windows.add_polygon([
            (x - win_w/2, y_bot - win_h/2),
            (x + win_w/2, y_bot - win_h/2),
            (x + win_w/2, y_bot + win_h/2),
            (x - win_w/2, y_bot + win_h/2)
        ], layer=layer)
    
    bot_result = gf.boolean(bot_bar, bot_windows, operation="not", layer=layer)
    c << bot_result
    
    return c

# Generate and save
device = chain_link_device()
device.write_gds("chain_link_device.gds")