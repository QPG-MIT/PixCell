import gdsfactory as gf

@gf.cell
def improved_coupler() -> gf.Component:
    # 1. Constants based on 120um x 4um footprint
    L_TOTAL = 120.0
    H_TOTAL = 4.0
    WG_WIDTH = 0.7  # Slightly wider for better visual match
    GAP = 0.1       # Much narrower gap for the coupling region
    
    # Define lengths for segments
    L_ARM = 10.0      # Straight input/output sections
    L_COUPLE = 60.0   # Central coupling section
    L_TRANS = (L_TOTAL - L_COUPLE - 2 * L_ARM) / 2 # ~20um transition zone
    
    # 2. Calculate vertical offsets for centerlines
    # Top of device is at H_TOTAL/2 (2.0), bottom of waveguide is at 2.0 - WG_WIDTH
    y_outer = (H_TOTAL / 2) - (WG_WIDTH / 2) # Outer centerline
    y_inner = (GAP / 2) + (WG_WIDTH / 2)     # Inner centerline
    
    # 3. Create the Path for the top branch
    # Waypoints: Start -> End of Arm -> Start of Coupling -> End of Coupling -> End of Transition -> Finish
    points = [
        (0, y_outer),
        (L_ARM, y_outer),
        (L_ARM + L_TRANS, y_inner),
        (L_ARM + L_TRANS + L_COUPLE, y_inner),
        (L_TOTAL - L_ARM, y_outer),
        (L_TOTAL, y_outer),
    ]
    
    # Create smooth path with Euler bends (radius=15 provides the "natural" curve)
    path = gf.path.smooth(points=points, radius=15.0)
    
    # 4. Create Cross Section
    xs = gf.cross_section.cross_section(width=WG_WIDTH, layer=(1, 0))
    
    # 5. Assemble the Component
    c = gf.Component("improved_coupler")
    
    # Extrude the path for the top waveguide
    top_wg = c << gf.path.extrude(path, cross_section=xs)
    
    # Create the bottom waveguide by mirroring the top one
    bot_wg = c << gf.path.extrude(path, cross_section=xs)
    bot_wg.mirror_y()
    
    return c

if __name__ == "__main__":
    c = improved_coupler()
    c.write_gds("improved_coupler.gds")
    c.show()