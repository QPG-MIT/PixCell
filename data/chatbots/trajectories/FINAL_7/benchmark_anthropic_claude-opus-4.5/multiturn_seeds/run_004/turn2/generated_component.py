import gdsfactory as gf

@gf.cell
def chain_link_device():
    """
    Creates a chain link structure with:
    - Thick outer stadium/capsule border
    - Two horizontal link bars with rectangular cutouts
    """
    c = gf.Component()
    layer = (1, 0)
    
    # Device dimensions based on footprint
    WIDTH = 5.5
    HEIGHT = 3.0
    
    # Frame thickness
    FRAME_THICKNESS = 0.32
    
    def make_stadium(w, h, lyr):
        """Create a stadium shape (rectangle with semicircular ends)"""
        stadium = gf.Component()
        
        radius = h / 2
        rect_length = max(0, w - h)
        
        if rect_length > 0:
            rect = gf.components.rectangle(size=(rect_length, h), layer=lyr, centered=True)
            stadium << rect
        
        left_cap = gf.components.circle(radius=radius, layer=lyr)
        left_ref = stadium << left_cap
        left_ref.move((-rect_length / 2, 0))
        
        right_cap = gf.components.circle(radius=radius, layer=lyr)
        right_ref = stadium << right_cap
        right_ref.move((rect_length / 2, 0))
        
        return stadium
    
    # === CREATE OUTER FRAME ===
    outer_shape = make_stadium(WIDTH, HEIGHT, layer)
    
    inner_width = WIDTH - 2 * FRAME_THICKNESS
    inner_height = HEIGHT - 2 * FRAME_THICKNESS
    inner_shape = make_stadium(inner_width, inner_height, layer)
    
    outer_frame = gf.boolean(outer_shape, inner_shape, operation="not", layer=layer)
    c << outer_frame
    
    # === CREATE INNER LINK BARS ===
    BAR_HEIGHT = 0.58
    BAR_GAP = 0.20
    BAR_WIDTH = inner_width - 0.15
    
    # Cutout dimensions - wider rectangles
    CUT_WIDTH = 0.62
    CUT_HEIGHT = BAR_HEIGHT * 0.42
    
    # Vertical positions
    top_y = (BAR_GAP + BAR_HEIGHT) / 2
    bottom_y = -top_y
    
    # --- Top bar with 3 cutouts ---
    top_bar = make_stadium(BAR_WIDTH, BAR_HEIGHT, layer)
    
    top_cuts = gf.Component()
    TOP_CUT_SPACING = 0.95
    for x_pos in [-TOP_CUT_SPACING, 0, TOP_CUT_SPACING]:
        cut = gf.components.rectangle(size=(CUT_WIDTH, CUT_HEIGHT), layer=layer, centered=True)
        cut_ref = top_cuts << cut
        cut_ref.move((x_pos, 0))
    
    top_bar_with_cuts = gf.boolean(top_bar, top_cuts, operation="not", layer=layer)
    top_ref = c << top_bar_with_cuts
    top_ref.move((0, top_y))
    
    # --- Bottom bar with 2 cutouts ---
    bottom_bar = make_stadium(BAR_WIDTH, BAR_HEIGHT, layer)
    
    bottom_cuts = gf.Component()
    BOTTOM_CUT_SPACING = 0.75
    for x_pos in [-BOTTOM_CUT_SPACING, BOTTOM_CUT_SPACING]:
        cut = gf.components.rectangle(size=(CUT_WIDTH, CUT_HEIGHT), layer=layer, centered=True)
        cut_ref = bottom_cuts << cut
        cut_ref.move((x_pos, 0))
    
    bottom_bar_with_cuts = gf.boolean(bottom_bar, bottom_cuts, operation="not", layer=layer)
    bottom_ref = c << bottom_bar_with_cuts
    bottom_ref.move((0, bottom_y))
    
    return c


# Create and save
if __name__ == "__main__":
    device = chain_link_device()
    device.write_gds("chain_link_device.gds")
    print("GDS file saved as 'chain_link_device.gds'")