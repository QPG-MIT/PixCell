import gdsfactory as gf

@gf.cell
def recreate_image_device():
    """
    Recreates the target image with fixed vertical spacing to prevent smoothing errors.
    Footprint: 120um x 4um.
    """
    c = gf.Component("recreated_device_fixed")
    
    # Dimensions & Layers
    WIDTH_LIMIT = 120.0
    HALF_H = 2.0  # Total height 4um
    LAYER = (1, 0)
    
    # Feature Sizes
    w_thin = 0.06    # Thinner lines
    w_thick = 0.5    # The prominent thick bars in U-stacks
    gap = 0.1        # Spacing between elements
    r_bend = 0.05    # Small radius for sharp but smooth transitions
    
    # Define Cross-Sections
    xs_thin = gf.cross_section.cross_section(width=w_thin, layer=LAYER)
    xs_thick = gf.cross_section.cross_section(width=w_thick, layer=LAYER)
    
    # ------------------------------------------------------------------
    # 1. CENTRAL HORIZONTAL STACK (5 Waveguides)
    # ------------------------------------------------------------------
    num_central = 5
    central_span = 110.0
    # Center the 5-line stack around y=0
    for i in range(num_central):
        y_pos = (i - (num_central - 1) / 2) * (w_thin + gap)
        line = c << gf.components.straight(length=central_span, cross_section=xs_thin)
        line.x = 0
        line.y = y_pos

    # ------------------------------------------------------------------
    # 2. U-SHAPED STACKS (Top and Bottom)
    # ------------------------------------------------------------------
    def add_u_stack(direction=1):
        """Adds a stack of 1 thick and 4 thin U-shaped waveguides."""
        sgn = 1 if direction > 0 else -1
        
        # Position the thick block inside the U-stack
        # It sits clear of the central stack (which ends at ~0.35um)
        y_thick_base = 0.7 * sgn
        
        # A. Inner Thick Waveguide
        thick_span = 100.0
        pts_thick = [
            (-thick_span/2, HALF_H * sgn), # Vertical arm start at edge
            (-thick_span/2, y_thick_base), # Corner 1
            (thick_span/2, y_thick_base),  # Corner 2
            (thick_span/2, HALF_H * sgn)   # Vertical arm end at edge
        ]
        path_thick = gf.path.smooth(points=pts_thick, radius=r_bend)
        c << gf.path.extrude(path_thick, cross_section=xs_thick)
        
        # B. 4 Outer Thin Waveguides
        # These stack "outward" (away from the center)
        for i in range(4):
            # Distance from thick block center:
            # offset = (thick/2 + gap) + i*(thin + gap) + thin/2
            offset = (w_thick/2 + gap) + i * (w_thin + gap) + w_thin/2
            y_curr = y_thick_base + (offset * sgn)
            
            # Increase span slightly for each outer line to "fan" the arms
            curr_span = thick_span + (i + 1) * 2.0
            
            pts = [
                (-curr_span/2, HALF_H * sgn),
                (-curr_span/2, y_curr),
                (curr_span/2, y_curr),
                (curr_span/2, HALF_H * sgn)
            ]
            
            path = gf.path.smooth(points=pts, radius=r_bend)
            c << gf.path.extrude(path, cross_section=xs_thin)

    # Render top and bottom features
    add_u_stack(direction=1)
    add_u_stack(direction=-1)

    return c

if __name__ == "__main__":
    device = recreate_image_device()
    device.write_gds("recreated_device.gds")
    print(f"GDS generated successfully. BBox: {device.bbox}")