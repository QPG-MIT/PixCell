import gdsfactory as gf

@gf.cell
def racetrack_mzi_device():
    """
    Recreates the device with a thick racetrack frame and an internal 
    Mach-Zehnder interferometer structure with modulation blocks.
    Footprint: 5.5um (width) x 3.0um (height)
    """
    c = gf.Component()
    
    # --- Dimensions & Constants ---
    width = 5.5
    height = 3.0
    layer = (1, 0)
    
    # Thicknesses and sizes based on visual inspection
    frame_thickness = 0.55
    inner_wg_width = 0.22
    block_size = (0.8, 0.45) # Width, Height
    branch_y_offset = 0.55   # Vertical separation of the arms
    
    # --- 1. Create the Racetrack Frame ---
    # We construct the frame using boolean subtraction to ensure a perfect closed loop.
    def make_filled_racetrack(w, h):
        ls = w - h # Length of straight section
        rt = gf.Component()
        # Central rectangle
        rt << gf.components.rectangle(size=(ls, h), layer=layer, centered=True)
        # Semicircle ends
        c1 = rt << gf.components.circle(radius=h/2, layer=layer)
        c1.movex(-ls/2)
        c2 = rt << gf.components.circle(radius=h/2, layer=layer)
        c2.movex(ls/2)
        return rt

    outer_rt = make_filled_racetrack(width, height)
    inner_rt = make_filled_racetrack(width - 2*frame_thickness, height - 2*frame_thickness)
    
    frame = gf.boolean(outer_rt, inner_rt, operation="not", layer=layer)
    c << frame # Frame is now a single centered component

    # --- 2. Create the Internal Arms ---
    # The inner cavity boundary is at x = +/- (width/2 - frame_thickness)
    x_boundary = (width / 2) - frame_thickness
    
    # Path waypoints for the top branch (S-curve split)
    # Start/End at the center of the inner curves
    pts_top = [
        (-x_boundary, 0),
        (-x_boundary + 0.4, 0),      # Trunk
        (-x_boundary + 1.1, branch_y_offset), # Smooth split
        (x_boundary - 1.1, branch_y_offset),  # Parallel section
        (x_boundary - 0.4, 0),       # Smooth merge
        (x_boundary, 0)
    ]
    
    # Mirror for the bottom branch
    pts_bot = [(x, -y) for x, y in pts_top]
    
    xs_inner = gf.cross_section.cross_section(width=inner_wg_width, layer=layer)
    
    # Extrude smoothed paths to replicate the adiabatic transitions
    c << gf.path.extrude(gf.path.smooth(pts_top, radius=0.4), cross_section=xs_inner)
    c << gf.path.extrude(gf.path.smooth(pts_bot, radius=0.4), cross_section=xs_inner)

    # --- 3. Create the Modulation Blocks ---
    # Four rectangular blocks, two per arm, placed symmetrically
    rect_block = gf.components.rectangle(size=block_size, layer=layer, centered=True)
    
    x_positions = [-0.65, 0.65] # Centers for the blocks along the horizontal segments
    
    for x in x_positions:
        # Top branch blocks
        ref_top = c << rect_block
        ref_top.move((x, branch_y_offset))
        
        # Bottom branch blocks
        ref_bot = c << rect_block
        ref_bot.move((x, -branch_y_offset))

    return c

if __name__ == "__main__":
    # Generate and display
    device = racetrack_mzi_device()
    device.write_gds("racetrack_mzi.gds")
    device.show()