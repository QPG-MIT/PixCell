import gdsfactory as gf

@gf.cell
def bottle_carrier():
    """
    Creates a bottle carrier icon with 4 bottle necks protruding from a crate,
    and a triangular pointer at the bottom center.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # Overall dimensions to fit footprint [25, 10]
    width = 25
    
    # Y coordinates defining the vertical structure
    y_tip = 0           # bottom tip of triangle pointer
    y_base = 0.8        # bottom of main box
    y_box_top = 5.0     # top of main box / base of bottle necks  
    y_top = 10.0        # top of bottle necks
    
    # Bottle parameters - 4 bottles evenly distributed
    n_bottles = 4
    section_width = width / n_bottles  # 6.25 per section
    neck_base_width = 4.8              # width at box top level
    neck_top_width = 2.2               # width at top (narrower)
    
    # Triangle pointer at bottom
    tri_half_width = 1.0
    
    # Build polygon outline clockwise from bottom-left
    points = []
    
    # Start at bottom-left of box
    points.append((0, y_base))
    
    # Up to top-left of box  
    points.append((0, y_box_top))
    
    # Trace each bottle neck from left to right
    for i in range(n_bottles):
        cx = section_width * (i + 0.5)  # center x of bottle
        
        lb = cx - neck_base_width / 2   # left x at base
        rb = cx + neck_base_width / 2   # right x at base
        lt = cx - neck_top_width / 2    # left x at top
        rt = cx + neck_top_width / 2    # right x at top
        
        # Move to left base of bottle (horizontal segment at box top)
        points.append((lb, y_box_top))
        # Up the left side of neck (tapers inward)
        points.append((lt, y_top))
        # Across the top of bottle
        points.append((rt, y_top))
        # Down the right side of neck (tapers outward)
        points.append((rb, y_box_top))
    
    # After last bottle, continue to right edge of box
    points.append((width, y_box_top))
    
    # Down right side of box
    points.append((width, y_base))
    
    # Along bottom edge with triangle protrusion pointing down
    points.append((width / 2 + tri_half_width, y_base))
    points.append((width / 2, y_tip))  # triangle tip pointing down
    points.append((width / 2 - tri_half_width, y_base))
    
    # Polygon auto-closes back to starting point (0, y_base)
    
    c.add_polygon(points, layer=layer)
    
    return c

# Create and save the device
device = bottle_carrier()
device.write_gds("bottle_carrier.gds")