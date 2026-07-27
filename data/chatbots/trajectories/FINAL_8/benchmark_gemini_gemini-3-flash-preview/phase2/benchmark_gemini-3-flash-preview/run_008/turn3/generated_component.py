import gdsfactory as gf

@gf.cell
def recreate_final_geometry_v5():
    c = gf.Component("refined_device_v5")
    layer = (1, 0)
    
    # --- DIMENSIONS ---
    # Total footprint: 120um x 4um
    total_w = 120.0
    inner_w = 92.0  # Width of the internal bars (46um from center)
    
    h_thin = 0.05   # Thickness of grating lines
    pitch = 0.12    # Center-to-center spacing
    h_thick = 0.85  # Height of the main blocks
    
    # Helper to add and move rectangles safely
    def add_rect(w, h, x, y):
        rect = gf.components.rectangle(size=(w, h), layer=layer, centered=True)
        ref = c << rect
        ref.move((x, y))
        return ref

    # --- 1. CENTRAL GRATING (5 lines) ---
    # These span the full 120um width
    for i in range(5):
        y_pos = (i - 2) * pitch
        add_rect(total_w, h_thin, 0, y_pos)

    # --- 2. INTERNAL BODY STRUCTURES ---
    # Top Assembly: 1 thick block + 5 thin lines
    add_rect(inner_w, h_thick, 0, 1.0)
    for i in range(5):
        add_rect(inner_w, h_thin, 0, 1.55 + i * pitch)
        
    # Bottom Assembly: 1 thick block + 5 thin lines
    add_rect(inner_w, h_thick, 0, -1.0)
    for i in range(5):
        add_rect(inner_w, h_thin, 0, -(1.55 + i * pitch))

    # --- 3. SIDE BRACKETS (Concave Flared Walls) ---
    # We define the coordinates for the Top-Right quadrant bracket.
    # It starts just outside the inner bars (x=46) and curves outward.
    
    # Points defining the "pinched" flared shape
    bracket_pts = [
        (46.0, 0.35),   # Bottom-left (near central gap)
        (46.2, 0.8),    # Inner curve start
        (47.5, 1.4),    # Inner curve mid
        (51.0, 2.0),    # Top-left (flared out)
        (55.0, 2.0),    # Top-right (outer edge)
        (51.5, 1.4),    # Outer curve mid
        (50.2, 0.8),    # Outer curve end
        (50.0, 0.35)    # Bottom-right
    ]
    
    # Create the quadrant component
    bracket_quad = gf.components.polygon(points=bracket_pts, layer=layer)
    
    # Place all four mirrored versions
    # Top Right
    c << bracket_quad
    
    # Top Left
    tl = c << bracket_quad
    tl.mirror_x()
    
    # Bottom Right
    br = c << bracket_quad
    br.mirror_y()
    
    # Bottom Left
    bl = c << bracket_quad
    bl.mirror_x()
    bl.mirror_y()

    return c

if __name__ == "__main__":
    # Generate the component
    device = recreate_final_geometry_v5()
    
    # Save the GDS file
    device.write_gds("recreated_geometry_v5.gds")
    
    # Show in GDS viewer (KLayout)
    device.show()