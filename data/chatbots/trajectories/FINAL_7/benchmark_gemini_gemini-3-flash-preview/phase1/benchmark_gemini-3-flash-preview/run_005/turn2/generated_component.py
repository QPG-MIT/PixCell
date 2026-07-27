import gdsfactory as gf

@gf.cell
def recreated_device_final():
    """
    Recreates the device geometry with precise 5.5um x 3.0um footprint.
    Uses parametric primitives and handles boolean list outputs.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # --- 1. Dimensions based on [5.5, 3.0] Footprint ---
    total_w = 5.5
    total_h = 3.0
    r_outer = total_h / 2         # 1.5 um
    l_straight = total_w - 2 * r_outer  # 2.5 um (Straight section of the stadium)
    wall_thickness = 0.4          # Thickness of the frame
    r_inner = r_outer - wall_thickness
    
    # --- 2. Stadium Frame Construction ---
    # Construct stadium by ORing a rectangle and two circles
    def make_stadium_comp(length, radius):
        s = gf.Component()
        s << gf.components.rectangle(size=(length, 2 * radius), centered=True, layer=layer)
        c1 = s << gf.components.circle(radius=radius, layer=layer)
        c2 = s << gf.components.circle(radius=radius, layer=layer)
        c1.movex(-length / 2)
        c2.movex(length / 2)
        return s

    stadium_out = make_stadium_comp(l_straight, r_outer)
    stadium_in = make_stadium_comp(l_straight, r_inner)
    
    # Subtract inner from outer. We use a loop to handle potential list returns from boolean.
    frame_geom = gf.boolean(stadium_out, stadium_in, operation="not", layer=layer)
    if isinstance(frame_geom, list):
        for poly in frame_geom:
            c.add_polygon(poly, layer=layer)
    else:
        c << frame_geom

    # --- 3. Internal Branch Structure ---
    # Junction blocks at the ends of the internal straight section
    block_w = 0.5
    block_h = 0.95
    
    b_left = c << gf.components.rectangle(size=(block_w, block_h), centered=True, layer=layer)
    b_left.movex(-l_straight / 2 + block_w / 2)
    
    b_right = c << gf.components.rectangle(size=(block_w, block_h), centered=True, layer=layer)
    b_right.movex(l_straight / 2 - block_w / 2)
    
    # Arm and Pad parameters
    arm_y_offset = 0.65
    arm_thickness = 0.16
    slant_length = 0.3    # Horizontal distance for the diagonal part
    pad_w = 0.72          # Width of pads
    pad_h = 0.45          # Height of pads
    pad_gap = 0.18        # Gap between pads
    
    for y_sign in [1, -1]:
        y_pos = y_sign * arm_y_offset
        
        # Define a path that emerges from the junction block, slants, stays horizontal, then slants back
        # Path points: (start_x, start_y)
        path_points = [
            (-l_straight / 2 + block_w, 0),             # Start at center of side block
            (-l_straight / 2 + block_w + slant_length, y_pos), # Slant end
            (l_straight / 2 - block_w - slant_length, y_pos),  # Horizontal end
            (l_straight / 2 - block_w, 0)               # Slant back to center
        ]
        
        arm_path = gf.Path(path_points)
        c << gf.path.extrude(arm_path, width=arm_thickness, layer=layer)
        
        # Place two rectangular pads symmetrically on the horizontal segment of each arm
        p1 = c << gf.components.rectangle(size=(pad_w, pad_h), centered=True, layer=layer)
        p1.move((- (pad_w + pad_gap) / 2, y_pos))
        
        p2 = c << gf.components.rectangle(size=(pad_w, pad_h), centered=True, layer=layer)
        p2.move(((pad_w + pad_gap) / 2, y_pos))
        
    return c

if __name__ == "__main__":
    device = recreated_device_final()
    device.write_gds("recreated_device_v2.gds")
    # device.show() # Uncomment to view in KLayout