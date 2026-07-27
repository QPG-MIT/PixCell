import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreates the device geometry with a 5.5um x 3.0um footprint.
    Fixes the DBox subscripting error and refines the internal proportions.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # --- 1. Dimensions based on [5.5, 3.0] Footprint ---
    total_w = 5.5
    total_h = 3.0
    r_outer = total_h / 2         # 1.5 um
    l_straight = total_w - 2 * r_outer  # 2.5 um
    wall_thickness = 0.4          # Thickness of the stadium frame
    r_inner = r_outer - wall_thickness
    
    # --- 2. Stadium Frame Construction ---
    def make_stadium_comp(length, radius):
        s = gf.Component()
        # Main straight section
        s << gf.components.rectangle(size=(length, 2 * radius), centered=True, layer=layer)
        # Circular end caps
        c1 = s << gf.components.circle(radius=radius, layer=layer)
        c2 = s << gf.components.circle(radius=radius, layer=layer)
        c1.movex(-length / 2)
        c2.movex(length / 2)
        return s

    stadium_out = make_stadium_comp(l_straight, r_outer)
    stadium_in = make_stadium_comp(l_straight, r_inner)
    
    # Subtract inner from outer to create the hollow frame
    c << gf.boolean(stadium_out, stadium_in, operation="not", layer=layer)

    # --- 3. Internal Branch Structure ---
    # Vertical anchor blocks at the ends of the internal section
    anchor_w = 0.45
    anchor_h = 1.1
    # Move anchors slightly inward from the curve transition for better visual fit
    anchor_x = (l_straight / 2) - 0.2 
    
    l_anchor = c << gf.components.rectangle(size=(anchor_w, anchor_h), centered=True, layer=layer)
    l_anchor.movex(-anchor_x)
    
    r_anchor = c << gf.components.rectangle(size=(anchor_w, anchor_h), centered=True, layer=layer)
    r_anchor.movex(anchor_x)
    
    # Branching waveguide parameters
    arm_y_offset = 0.68   # Vertical distance of arms from centerline
    arm_thickness = 0.16
    stem_length = 0.25    # Length of horizontal segment from anchor before split
    slant_dx = 0.4        # Horizontal distance for the diagonal part of the fork
    
    x_start = -anchor_x + anchor_w/2
    x_end = anchor_x - anchor_w/2
    
    # Define the path for the top and bottom arms (Double-Y structure)
    for y_sign in [1, -1]:
        y_pos = y_sign * arm_y_offset
        # Path: Start at anchor -> stem -> slant to arm height -> horizontal segment -> slant back -> stem -> end anchor
        points = [
            (x_start, 0),
            (x_start + stem_length, 0),
            (x_start + stem_length + slant_dx, y_pos),
            (x_end - stem_length - slant_dx, y_pos),
            (x_end - stem_length, 0),
            (x_end, 0)
        ]
        arm_path = gf.Path(points)
        c << gf.path.extrude(arm_path, width=arm_thickness, layer=layer)
        
        # --- 4. Load Pads ---
        pad_w = 0.65
        pad_h = 0.45
        pad_gap = 0.15 # Gap between the two pads on a single arm
        
        # Place two rectangular pads on the horizontal segment of each arm
        p1 = c << gf.components.rectangle(size=(pad_w, pad_h), centered=True, layer=layer)
        p1.move((- (pad_w + pad_gap) / 2, y_pos))
        
        p2 = c << gf.components.rectangle(size=(pad_w, pad_h), centered=True, layer=layer)
        p2.move(((pad_w + pad_gap) / 2, y_pos))
        
    return c

if __name__ == "__main__":
    device = recreated_device()
    device.write_gds("recreated_device_v3.gds")
    
    # Fixed Footprint Check: Use .dxsize and .dysize to avoid DBox indexing error
    width = device.dxsize
    height = device.dysize
    print(f"Final Footprint: {width:.2f}um x {height:.2f}um")