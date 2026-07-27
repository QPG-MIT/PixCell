import gdsfactory as gf

@gf.cell
def recreate_target_device_final():
    """
    Recreates the target image with robust path geometries.
    Footprint: 120um x 4um.
    Nesting: Thick bar is the innermost of the U-stack.
    """
    c = gf.Component("target_device_v4_robust")
    
    # 1. Global Parameters
    X_TOTAL = 120.0
    Y_TOTAL = 4.0
    Y_MAX = Y_TOTAL / 2
    LAYER = (1, 0)
    
    # Feature Dimensions
    w_thin = 0.06
    w_mid = 0.1
    w_thick = 0.5
    gap = 0.1
    r_bend = 0.15 # Small enough to fit in the limited vertical space
    
    # ------------------------------------------------------------------
    # 2. CENTRAL STACK (5 lines)
    # ------------------------------------------------------------------
    xs_mid = gf.cross_section.cross_section(width=w_mid, layer=LAYER)
    num_mid = 5
    for i in range(num_mid):
        y_pos = (i - (num_mid - 1) / 2) * (w_mid + gap)
        line = c << gf.components.straight(length=X_TOTAL - 4.0, cross_section=xs_mid)
        line.x = 0
        line.y = y_pos

    # ------------------------------------------------------------------
    # 3. U-SHAPED STACKS (Top and Bottom)
    # ------------------------------------------------------------------
    def add_u_stack(direction=1):
        sgn = 1 if direction > 0 else -1
        
        # Calculate a base Y for the U-stack clear of the center
        # Center stack ends at ~0.5. Let's start the thick bar at 0.8
        y_thick_center = 0.8 * sgn
        span_thick = 104.0
        
        # A. Inner Thick Bar
        xs_thick = gf.cross_section.cross_section(width=w_thick, layer=LAYER)
        pts_thick = [
            (-span_thick/2, Y_MAX * sgn),
            (-span_thick/2, y_thick_center),
            (span_thick/2, y_thick_center),
            (span_thick/2, Y_MAX * sgn)
        ]
        path_thick = gf.path.smooth(points=pts_thick, radius=r_bend)
        c << gf.path.extrude(path_thick, cross_section=xs_thick)
        
        # B. 4 Outer Thin Lines
        # These wrap around the thick bar (further from y=0)
        xs_thin = gf.cross_section.cross_section(width=w_thin, layer=LAYER)
        
        for i in range(4):
            # Vertical offset: half-thick + gap + (i * thin/gap steps)
            offset = (w_thick/2 + gap) + i * (w_thin + gap) + w_thin/2
            y_curr = y_thick_center + (offset * sgn)
            
            # The vertical distance left is (Y_MAX - abs(y_curr)). 
            # We must ensure radius < this distance.
            dist_left = abs(Y_MAX) - abs(y_curr)
            safe_radius = min(r_bend, dist_left * 0.8)
            
            # Widening the span for each outer line
            span_curr = span_thick + (i + 1) * 3.0
            
            pts = [
                (-span_curr/2, Y_MAX * sgn),
                (-span_curr/2, y_curr),
                (span_curr/2, y_curr),
                (span_curr/2, Y_MAX * sgn)
            ]
            
            # If safe_radius is too small (e.g. < 0.01), use a simple path
            if safe_radius > 0.01:
                path = gf.path.smooth(points=pts, radius=safe_radius)
            else:
                path = gf.Path(pts)
                
            c << gf.path.extrude(path, cross_section=xs_thin)

    # Generate Top and Bottom
    add_u_stack(direction=1)
    add_u_stack(direction=-1)

    return c

if __name__ == "__main__":
    # Create the component
    device = recreate_target_device_final()
    
    # Export GDS
    device.write_gds("recreated_device_final.gds")
    
    # Final verification of dimensions
    bbox = device.bbox
    width = bbox[1][0] - bbox[0][0]
    height = bbox[1][1] - bbox[0][1]
    print(f"GDS Exported: 'recreated_device_final.gds'")
    print(f"Dimensions: {width:.2f}um x {height:.2f}um")