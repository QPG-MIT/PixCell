import gdsfactory as gf

@gf.cell
def mzi_racetrack_final():
    c = gf.Component("mzi_device")
    layer = (1, 0)
    
    # 1. DIMENSIONS & MATH
    # Goal: Total Width = 5.5, Total Height = 3.0
    total_w = 5.5
    total_h = 3.0
    ring_width = 0.75  # Thicker lines for bold appearance
    
    # Centerline radius calculation:
    # Height = 2 * R_centerline + ring_width
    # 3.0 = 2 * Rc + 0.75  => 2 * Rc = 2.25 => Rc = 1.125
    r_center = 1.125
    
    # Straight segment calculation:
    # Width = L_straight + 2 * (R_centerline + ring_width/2)
    # 5.5 = L + 2 * (1.125 + 0.375) => 5.5 = L + 3.0 => L = 2.5
    l_straight = 2.5

    # 2. CROSS SECTION
    # FIX: Explicitly set radius=r_center to override the 10um default limit
    xs = gf.cross_section.cross_section(width=ring_width, layer=layer, radius=r_center)

    # 3. OUTER RACETRACK FRAME
    rt = gf.Component("frame")
    # Top/Bottom Straights
    s_top = rt << gf.components.straight(length=l_straight, cross_section=xs)
    s_top.move((-l_straight/2, r_center))
    s_bot = rt << gf.components.straight(length=l_straight, cross_section=xs)
    s_bot.move((-l_straight/2, -r_center))
    
    # Left/Right Bends
    b_left = rt << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs)
    b_left.rotate(90)
    b_left.move((-l_straight/2, 0))
    b_right = rt << gf.components.bend_circular(radius=r_center, angle=180, cross_section=xs)
    b_right.rotate(-90)
    b_right.move((l_straight/2, 0))
    
    c << rt

    # 4. INNER MZI STRUCTURE
    # Side feed blocks
    sb_w, sb_h = 0.75, 1.05
    inner_wall_x = l_straight/2 + (r_center - ring_width/2)
    
    lb = c << gf.components.rectangle(size=(sb_w, sb_h), layer=layer, centered=True)
    lb.movex(-inner_wall_x + sb_w/4) 
    rb = c << gf.components.rectangle(size=(sb_w, sb_h), layer=layer, centered=True)
    rb.movex(inner_wall_x - sb_w/4)
    
    # Arm Waveguides & Modulator Blocks
    arm_width = 0.3  # Thicker arms
    y_offset = 0.52 
    trans_dx = 0.45 
    
    x_start = -inner_wall_x + sb_w/4 + sb_w/2
    x_end = inner_wall_x - sb_w/4 - sb_w/2
    
    for y_sign in [1, -1]:
        y_pos = y_sign * y_offset
        
        # Angled paths
        pts = [
            (x_start, 0),
            (x_start + trans_dx, y_pos),
            (x_end - trans_dx, y_pos),
            (x_end, 0)
        ]
        c << gf.path.extrude(gf.Path(pts), width=arm_width, layer=layer)
        
        # Dual tuning blocks per arm
        h_w, h_h = 0.9, 0.58
        h_gap = 0.1
        
        h1 = c << gf.components.rectangle(size=(h_w, h_h), layer=layer, centered=True)
        h1.move((-h_w/2 - h_gap/2, y_pos))
        
        h2 = c << gf.components.rectangle(size=(h_w, h_h), layer=layer, centered=True)
        h2.move((h_w/2 + h_gap/2, y_pos))

    return c

if __name__ == "__main__":
    device = mzi_racetrack_final()
    device.show()
    device.write_gds("mzi_racetrack_v4.gds")