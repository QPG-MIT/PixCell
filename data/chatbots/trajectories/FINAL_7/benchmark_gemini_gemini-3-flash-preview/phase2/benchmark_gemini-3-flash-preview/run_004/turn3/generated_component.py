import gdsfactory as gf

@gf.cell
def racetrack_mzi_device():
    """
    Recreates the device with a thick racetrack frame and an internal 
    Mach-Zehnder interferometer structure with modulation blocks.
    Target Footprint: 5.5um (width) x 3.0um (height)
    """
    c = gf.Component()
    
    # --- Dimensions & Constants ---
    width = 5.5
    height = 3.0
    layer = (1, 0)
    
    # Proportions based on visual analysis
    frame_thickness = 0.5
    wg_width = 0.2
    block_size = (0.8, 0.4)     # Width, Height of each modulator block
    branch_y_offset = 0.5       # Vertical position of arms relative to center
    trunk_len = 0.45            # Length of horizontal start/end segments
    
    # --- 1. Create the Racetrack Frame ---
    # A stadium shape: two semicircles connected by a rectangle.
    # Total width = 5.5, Height = 3.0 -> Straight section length = 5.5 - 3.0 = 2.5
    def make_racetrack(w, h, layer):
        rt = gf.Component()
        ls = w - h 
        # Central rectangle
        rt << gf.components.rectangle(size=(ls, h), layer=layer, centered=True)
        # Circular caps
        cap1 = rt << gf.components.circle(radius=h/2, layer=layer)
        cap1.movex(-ls/2)
        cap2 = rt << gf.components.circle(radius=h/2, layer=layer)
        cap2.movex(ls/2)
        return rt

    outer = make_racetrack(width, height, layer)
    inner = make_racetrack(width - 2*frame_thickness, height - 2*frame_thickness, layer)
    
    frame = gf.boolean(outer, inner, operation="not", layer=layer)
    c << frame

    # --- 2. Create the Internal Arms ---
    # The inner cavity edge at y=0 is at x = +/- (width/2 - frame_thickness)
    x_inner_edge = (width / 2) - frame_thickness # 2.25
    
    # Defining points for the top arm path
    # Start at the left apex, go straight, S-bend up, stay horizontal, S-bend down, straight to right apex.
    # Transition happens between x=1.8 and x=1.2 (relative to center)
    x_split_start = x_inner_edge - trunk_len   # 1.8
    x_parallel_start = 1.2
    
    pts_top = [
        (-x_inner_edge, 0),
        (-x_split_start, 0),
        (-x_parallel_start, branch_y_offset),
        (x_parallel_start, branch_y_offset),
        (x_split_start, 0),
        (x_inner_edge, 0)
    ]
    
    pts_bot = [(x, -y) for x, y in pts_top]
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # Extrude smoothed paths for adiabatic transitions
    c << gf.path.extrude(gf.path.smooth(pts_top, radius=0.4), cross_section=xs)
    c << gf.path.extrude(gf.path.smooth(pts_bot, radius=0.4), cross_section=xs)

    # --- 3. Create the Modulation Blocks ---
    # Symmetrically placed on the parallel horizontal arm segments.
    rect_block = gf.components.rectangle(size=block_size, layer=layer, centered=True)
    
    # Two blocks per arm, separated by a thin gap in the middle
    x_block_positions = [-0.425, 0.425] 
    
    for x in x_block_positions:
        # Top branch blocks
        b_top = c << rect_block
        b_top.move((x, branch_y_offset))
        
        # Bottom branch blocks
        b_bot = c << rect_block
        b_bot.move((x, -branch_y_offset))

    return c

if __name__ == "__main__":
    device = racetrack_mzi_device()
    device.write_gds("racetrack_mzi_v3.gds")
    device.show()