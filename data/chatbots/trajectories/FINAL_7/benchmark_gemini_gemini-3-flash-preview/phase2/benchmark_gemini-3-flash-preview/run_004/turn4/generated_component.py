import gdsfactory as gf

@gf.cell
def racetrack_mzi_device():
    """
    Refined racetrack device with internal split-branch structure.
    Target Footprint: 5.5um (width) x 3.0um (height)
    """
    c = gf.Component()
    
    # --- Dimensions ---
    width = 5.5
    height = 3.0
    layer = (1, 0)
    
    # Visual proportions
    frame_thickness = 0.6
    wg_width = 0.28
    block_size = (0.75, 0.45)
    branch_y_offset = 0.55  # Distance from center to arm axis
    trunk_len = 0.55        # Length of the horizontal part before splitting
    slant_len = 0.5         # Horizontal span of the angled segment
    
    # --- 1. Create the Racetrack Frame ---
    # Total width = straight_len + 2 * radius
    # 5.5 = straight_len + 3.0  => straight_len = 2.5
    def make_racetrack(w, h, l_idx):
        rt = gf.Component()
        s_len = w - h
        radius = h / 2
        # Central rectangle
        rt << gf.components.rectangle(size=(s_len, h), layer=l_idx, centered=True)
        # Circular caps
        c1 = rt << gf.components.circle(radius=radius, layer=l_idx)
        c1.movex(-s_len / 2)
        c2 = rt << gf.components.circle(radius=radius, layer=l_idx)
        c2.movex(s_len / 2)
        return rt

    outer = make_racetrack(width, height, layer)
    inner = make_racetrack(width - 2*frame_thickness, height - 2*frame_thickness, layer)
    
    frame = gf.boolean(outer, inner, operation="not", layer=layer)
    c << frame

    # --- 2. Create the Internal Arms ---
    # Inner wall apex is at x = +/- (width/2 - frame_thickness) = +/- 2.15
    x_inner_edge = (width / 2) - frame_thickness
    
    # Define characteristic points for the top arm
    # Trunk -> Slant -> Parallel -> Slant -> Trunk
    x1 = -x_inner_edge           # -2.15
    x2 = x1 + trunk_len          # -1.6
    x3 = x2 + slant_len           # -1.1
    x4 = -x3                     # 1.1
    x5 = -x2                     # 1.6
    x6 = -x1                     # 2.15
    
    pts_top = [
        (x1, 0),
        (x2, 0),
        (x3, branch_y_offset),
        (x4, branch_y_offset),
        (x5, 0),
        (x6, 0)
    ]
    
    pts_bot = [(x, -y) for x, y in pts_top]
    
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # Smooth paths for transitions similar to the image
    c << gf.path.extrude(gf.path.smooth(pts_top, radius=0.3), cross_section=xs)
    c << gf.path.extrude(gf.path.smooth(pts_bot, radius=0.3), cross_section=xs)

    # --- 3. Create the Modulation Blocks ---
    # Two per arm, separated by a 0.1um gap at the center (x=0)
    block = gf.components.rectangle(size=block_size, layer=layer, centered=True)
    
    block_gap = 0.1
    x_offset = (block_size[0] / 2) + (block_gap / 2)
    
    positions = [
        (x_offset, branch_y_offset),   # Top Right
        (-x_offset, branch_y_offset),  # Top Left
        (x_offset, -branch_y_offset),  # Bottom Right
        (-x_offset, -branch_y_offset)  # Bottom Left
    ]
    
    for pos in positions:
        b_ref = c << block
        b_ref.move(pos)

    return c

if __name__ == "__main__":
    device = racetrack_mzi_device()
    device.write_gds("racetrack_mzi_v4.gds")
    device.show()