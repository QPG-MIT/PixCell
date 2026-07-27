import gdsfactory as gf

@gf.cell
def four_petal_cross():
    """
    Four-petal cross structure with thin stems extending from tips.
    Total footprint: 4.7 x 4.7 um
    """
    c = gf.Component()
    layer = (1, 0)
    
    # === Dimensions (adjusted to match target) ===
    # Horizontal ellipse - very elongated (wide and thin)
    h_rx = 1.7    # x half-length (long)
    h_ry = 0.32   # y half-width (thin)
    
    # Vertical ellipse - narrow and tall
    v_rx = 0.22   # x half-width (narrow)
    v_ry = 0.92   # y half-length
    
    # Stem dimensions - thin lines
    stem_width = 0.06
    h_stem_length = 0.65  # 2.35 - 1.7 = 0.65
    v_stem_length = 0.56
    
    # Overlap at center for solid fill
    overlap = 0.05
    v_offset = v_ry - overlap  # = 0.87
    
    # === Create base shapes ===
    h_ellipse = gf.components.ellipse(radii=(h_rx, h_ry), layer=layer)
    v_ellipse = gf.components.ellipse(radii=(v_rx, v_ry), layer=layer)
    h_stem_rect = gf.components.rectangle(size=(h_stem_length, stem_width), layer=layer, centered=True)
    v_stem_rect = gf.components.rectangle(size=(stem_width, v_stem_length), layer=layer, centered=True)
    
    # === Place horizontal ellipse (centered at origin) ===
    c << h_ellipse
    
    # === Place vertical ellipses ===
    top_v = c << v_ellipse
    top_v.move((0, v_offset))
    
    bottom_v = c << v_ellipse
    bottom_v.move((0, -v_offset))
    
    # === Place horizontal stems at ellipse tips ===
    h_stem_pos = h_rx + h_stem_length / 2
    
    right_stem = c << h_stem_rect
    right_stem.move((h_stem_pos, 0))
    
    left_stem = c << h_stem_rect
    left_stem.move((-h_stem_pos, 0))
    
    # === Place vertical stems at ellipse tips ===
    v_stem_pos = v_offset + v_ry + v_stem_length / 2
    
    top_stem = c << v_stem_rect
    top_stem.move((0, v_stem_pos))
    
    bottom_stem = c << v_stem_rect
    bottom_stem.move((0, -v_stem_pos))
    
    return c


# Create and save
device = four_petal_cross()
device.write_gds("four_petal_cross.gds")