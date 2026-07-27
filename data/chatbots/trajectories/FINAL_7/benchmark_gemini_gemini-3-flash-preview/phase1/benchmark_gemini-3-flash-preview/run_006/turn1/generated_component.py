import gdsfactory as gf

@gf.cell
def mzi_racetrack_device():
    c = gf.Component()
    layer = (1, 0)
    
    # 1. Dimensions based on footprint [3.0, 5.5]
    total_width = 5.5
    total_height = 3.0
    track_width = 0.45
    radius = total_height / 2
    l_straight = total_width - (2 * radius) # 2.5 um

    # 2. Outer Racetrack Frame
    # We create a path for the racetrack and extrude it
    p_frame = gf.path.straight(length=l_straight)
    p_frame.append(gf.path.arc(radius=radius - track_width/2, angle=180))
    p_frame.append(gf.path.straight(length=l_straight))
    p_frame.append(gf.path.arc(radius=radius - track_width/2, angle=180))
    
    frame = gf.path.extrude(p_frame, width=track_width, layer=layer)
    frame_ref = c << frame
    frame_ref.movex(-l_straight / 2) # Center the frame at origin

    # 3. Inner Structure (MZI)
    inner = gf.Component("inner_mzi")
    
    # Feed blocks at the sides
    block_size = (0.5, 0.9)
    left_feed = inner << gf.components.rectangle(size=block_size, layer=layer, centered=True)
    left_feed.movex(-2.3)
    right_feed = inner << gf.components.rectangle(size=block_size, layer=layer, centered=True)
    right_feed.movex(2.3)
    
    # Arms parameters
    arm_width = 0.18
    arm_y_offset = 0.65
    
    # Create top and bottom arms using paths
    # Coordinates chosen to match the visual proportions of the MZI branches
    pts_top = [(-2.3, 0), (-1.7, arm_y_offset), (1.7, arm_y_offset), (2.3, 0)]
    pts_bot = [(-2.3, 0), (-1.7, -arm_y_offset), (1.7, -arm_y_offset), (2.3, 0)]
    
    path_top = gf.Path(pts_top)
    path_bot = gf.Path(pts_bot)
    
    inner << gf.path.extrude(path_top, width=arm_width, layer=layer)
    inner << gf.path.extrude(path_bot, width=arm_width, layer=layer)
    
    # Heater / Rectangular tuning blocks on the arms
    rect_w, rect_h = 0.8, 0.5
    rect_gap = 0.1
    
    for y_sign in [1, -1]:
        y_pos = y_sign * arm_y_offset
        # Left heater block
        hl = inner << gf.components.rectangle(size=(rect_w, rect_h), layer=layer, centered=True)
        hl.move((-rect_w/2 - rect_gap/2, y_pos))
        # Right heater block
        hr = inner << gf.components.rectangle(size=(rect_w, rect_h), layer=layer, centered=True)
        hr.move((rect_w/2 + rect_gap/2, y_pos))

    # 4. Combine everything into a final component using a boolean OR
    # This ensures the overlapping regions are merged into a single polygon set
    final_device = gf.Component("recreated_device")
    combined_geom = gf.boolean(A=frame, B=inner, operation="or", layer=layer)
    final_device << combined_geom

    return final_device

if __name__ == "__main__":
    # Create the component
    my_device = mzi_racetrack_device()
    
    # Show in layout viewer if installed, or save to GDS
    my_device.show()
    my_device.write_gds("mzi_racetrack.gds")