import gdsfactory as gf

@gf.cell
def flower_device():
    """
    Creates a 4-petaled flower shape with rectangular tabs.
    Footprint ~4.7um x 4.7um.
    """
    layer = (1, 0)
    
    # Dimensions adjusted to fit ~4.7um footprint
    # (1.75 + 0.6) * 2 = 4.7um
    petal_rx = 0.6
    petal_ry = 1.75
    tab_width = 0.4
    tab_len = 0.6
    
    # 1. Create the base components (not references yet)
    p1 = gf.components.ellipse(radii=(petal_rx, petal_ry), layer=layer)
    p2 = gf.components.ellipse(radii=(petal_ry, petal_rx), layer=layer)
    
    t_n = gf.components.rectangle(size=(tab_width, tab_len), layer=layer, centered=True)
    t_n.movey(petal_ry + tab_len / 2)
    
    t_s = gf.components.rectangle(size=(tab_width, tab_len), layer=layer, centered=True)
    t_s.movey(-(petal_ry + tab_len / 2))
    
    t_e = gf.components.rectangle(size=(tab_len, tab_width), layer=layer, centered=True)
    t_e.movex(petal_ry + tab_len / 2)
    
    t_w = gf.components.rectangle(size=(tab_len, tab_width), layer=layer, centered=True)
    t_w.movex(-(petal_ry + tab_len / 2))
    
    # 2. Merge components using boolean OR
    # We chain the boolean operations to combine all parts into one polygon
    parts = [p1, p2, t_n, t_s, t_e, t_w]
    
    # Start with the first part
    merged = parts[0]
    
    # Iteratively combine the rest
    for part in parts[1:]:
        merged = gf.boolean(merged, part, operation="or", layer=layer)
        
    return merged

# Generate and view the device
device = flower_device()
device.show()