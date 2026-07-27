import gdsfactory as gf

@gf.cell
def chain_link_device():
    c = gf.Component()
    layer = (1, 0)
    
    # Device parameters (5.5 x 3.0 μm footprint)
    W = 5.5
    H = 3.0
    ring_t = 0.28
    
    # Stadium dimensions
    R = H / 2  # Radius of semicircular ends
    S = W - H  # Length of straight section
    
    # ===== CREATE OUTER STADIUM RING =====
    outer = gf.Component()
    outer << gf.components.rectangle(size=(S, H), layer=layer, centered=True)
    left_outer = outer << gf.components.circle(radius=R, layer=layer)
    left_outer.move((-S/2, 0))
    right_outer = outer << gf.components.circle(radius=R, layer=layer)
    right_outer.move((S/2, 0))
    
    # Inner stadium for hollow center
    inner_R = R - ring_t
    inner_H = H - 2*ring_t
    inner = gf.Component()
    inner << gf.components.rectangle(size=(S, inner_H), layer=layer, centered=True)
    left_inner = inner << gf.components.circle(radius=inner_R, layer=layer)
    left_inner.move((-S/2, 0))
    right_inner = inner << gf.components.circle(radius=inner_R, layer=layer)
    right_inner.move((S/2, 0))
    
    # Boolean subtraction for ring
    ring = gf.boolean(outer, inner, operation="not", layer=layer)
    c << ring
    
    # ===== CREATE INTERNAL BAR STRUCTURES =====
    bar_h = 0.40
    frame_w = 0.08
    win_h = bar_h - 2*frame_w
    win_w = 0.52
    cell_pitch = win_w + 2*frame_w
    
    # Bar extends across inner region into curved ends
    bar_len = S + 2*inner_R * 0.75
    
    # ----- Top bar (3 windows) -----
    y_top = 0.44
    
    top_solid = gf.Component()
    ts_rect = top_solid << gf.components.rectangle(size=(bar_len, bar_h), layer=layer, centered=True)
    ts_rect.move((0, y_top))
    
    top_holes = gf.Component()
    for i in range(3):
        x = (i - 1) * cell_pitch
        th_rect = top_holes << gf.components.rectangle(size=(win_w, win_h), layer=layer, centered=True)
        th_rect.move((x, y_top))
    
    top_bar = gf.boolean(top_solid, top_holes, operation="not", layer=layer)
    c << top_bar
    
    # ----- Bottom bar (2 windows) -----
    y_bottom = -0.44
    
    bottom_solid = gf.Component()
    bs_rect = bottom_solid << gf.components.rectangle(size=(bar_len, bar_h), layer=layer, centered=True)
    bs_rect.move((0, y_bottom))
    
    bottom_holes = gf.Component()
    for i in range(2):
        x = (i - 0.5) * cell_pitch
        bh_rect = bottom_holes << gf.components.rectangle(size=(win_w, win_h), layer=layer, centered=True)
        bh_rect.move((x, y_bottom))
    
    bottom_bar = gf.boolean(bottom_solid, bottom_holes, operation="not", layer=layer)
    c << bottom_bar
    
    return c

# Generate and save the device
device = chain_link_device()
device.write_gds("chain_link_device.gds")