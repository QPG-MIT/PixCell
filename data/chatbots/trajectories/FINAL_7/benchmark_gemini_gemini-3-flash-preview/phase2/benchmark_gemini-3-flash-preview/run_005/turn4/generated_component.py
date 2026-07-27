import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreates the device geometry within a 5.5um x 3.0um footprint.
    Matches the proportions, connectivity, and layout of the target image.
    """
    c = gf.Component()
    layer = (1, 0)
    
    # --- 1. Dimensions based on [5.5, 3.0] Footprint ---
    total_w = 5.5
    total_h = 3.0
    r_outer = total_h / 2         # 1.5 um radius for a 3um height
    l_straight = total_w - 2 * r_outer  # 2.5 um straight section
    wall_thickness = 0.42         # Frame thickness
    
    # Stadium Frame Construction
    def make_stadium_base(length, radius):
        s = gf.Component()
        # Main straight section
        s << gf.components.rectangle(size=(length, 2 * radius), centered=True, layer=layer)
        # Circular end caps
        c1 = s << gf.components.circle(radius=radius, layer=layer)
        c2 = s << gf.components.circle(radius=radius, layer=layer)
        c1.movex(-length / 2)
        c2.movex(length / 2)
        return s

    stadium_out = make_stadium_base(l_straight, r_outer)
    stadium_in = make_stadium_base(l_straight, r_outer - wall_thickness)
    
    # Create the hollow frame
    c << gf.boolean(stadium_out, stadium_in, operation="not", layer=layer)

    # --- 2. Internal Side Anchors ---
    # These are the thick blocks on the left and right inner edges.
    # Inner opening width is approx 4.6um (from -2.3 to 2.3).
    anchor_w = 0.75
    anchor_h = 1.45
    anchor_x_pos = 1.9  # Center position to align with inner curves
    
    for x_sign in [1, -1]:
        anchor = c << gf.components.rectangle(size=(anchor_w, anchor_h), centered=True, layer=layer)
        anchor.movex(x_sign * anchor_x_pos)
    
    # --- 3. Double-Arm Branching Structure ---
    arm_thickness = 0.24
    arm_y_offset = 0.62   # Vertical distance from centerline to arm center
    
    # Coordinates for the 'Y' branching path
    # Inner face of anchor is at roughly +/- 1.52
    x_inner_anchor = 1.52
    x_horizontal_start = 1.0
    
    for y_sign in [1, -1]:
        y_pos = y_sign * arm_y_offset
        # Path: anchor center -> short stem -> branch to arm height -> horizontal -> mirror
        points = [
            (-x_inner_anchor, 0),
            (-1.4, 0),              # Short stem before split
            (-x_horizontal_start, y_pos),
            (x_horizontal_start, y_pos),
            (1.4, 0),
            (x_inner_anchor, 0)
        ]
        arm_path = gf.Path(points)
        c << gf.path.extrude(arm_path, width=arm_thickness, layer=layer)
        
        # --- 4. Load Pads ---
        # Two rectangles placed on the horizontal segment of each arm.
        pad_w = 0.88
        pad_h = 0.44
        pad_gap = 0.12  # Small gap between the two pads
        
        # Centers for the two pads relative to x=0
        px = (pad_w + pad_gap) / 2
        
        p1 = c << gf.components.rectangle(size=(pad_w, pad_h), centered=True, layer=layer)
        p1.move((-px, y_pos))
        
        p2 = c << gf.components.rectangle(size=(pad_w, pad_h), centered=True, layer=layer)
        p2.move((px, y_pos))
        
    return c

if __name__ == "__main__":
    device = recreated_device()
    device.write_gds("recreated_device_v4.gds")
    
    # Final Footprint Verification
    width = device.dxsize
    height = device.dysize
    print(f"Final Footprint: {width:.2f}um x {height:.2f}um")