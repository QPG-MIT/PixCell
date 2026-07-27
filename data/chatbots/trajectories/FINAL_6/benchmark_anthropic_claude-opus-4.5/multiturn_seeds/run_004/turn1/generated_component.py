import gdsfactory as gf

@gf.cell
def four_petal_cross():
    """
    Four-petal cross structure with thin stems.
    Each petal is an ellipse with a thin stem extending outward.
    Total footprint: 4.7 x 4.7 um
    """
    c = gf.Component()
    
    layer = (1, 0)
    
    # Petal (ellipse) dimensions
    petal_half_width = 0.45   # Semi-axis perpendicular to arm direction
    petal_half_length = 0.95  # Semi-axis along arm direction
    
    # Stem dimensions
    stem_length = 0.55
    stem_width = 0.1
    
    # Overlap at center for solid fill (petals extend past center)
    overlap = 0.1
    
    # Create base shapes
    # Vertical ellipse (for top/bottom): taller than wide
    vertical_petal = gf.components.ellipse(radii=(petal_half_width, petal_half_length), layer=layer)
    # Horizontal ellipse (for left/right): wider than tall
    horizontal_petal = gf.components.ellipse(radii=(petal_half_length, petal_half_width), layer=layer)
    
    # Stem rectangles
    vertical_stem = gf.components.rectangle(size=(stem_width, stem_length), layer=layer, centered=True)
    horizontal_stem = gf.components.rectangle(size=(stem_length, stem_width), layer=layer, centered=True)
    
    # Calculate positions
    # Petal center offset from origin (accounting for overlap)
    petal_center_offset = petal_half_length - overlap
    # Stem center position (beyond petal outer edge)
    stem_center_offset = petal_center_offset + petal_half_length + stem_length / 2
    
    # === Top arm ===
    top_petal = c << vertical_petal
    top_petal.move((0, petal_center_offset))
    top_stem = c << vertical_stem
    top_stem.move((0, stem_center_offset))
    
    # === Bottom arm ===
    bottom_petal = c << vertical_petal
    bottom_petal.move((0, -petal_center_offset))
    bottom_stem = c << vertical_stem
    bottom_stem.move((0, -stem_center_offset))
    
    # === Right arm ===
    right_petal = c << horizontal_petal
    right_petal.move((petal_center_offset, 0))
    right_stem = c << horizontal_stem
    right_stem.move((stem_center_offset, 0))
    
    # === Left arm ===
    left_petal = c << horizontal_petal
    left_petal.move((-petal_center_offset, 0))
    left_stem = c << horizontal_stem
    left_stem.move((-stem_center_offset, 0))
    
    return c


# Create and save the device
device = four_petal_cross()
device.write_gds("four_petal_cross.gds")