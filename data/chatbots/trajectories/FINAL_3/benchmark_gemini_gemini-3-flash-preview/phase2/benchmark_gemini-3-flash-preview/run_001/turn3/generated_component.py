import gdsfactory as gf

@gf.cell
def directional_coupler_final() -> gf.Component:
    # 1. Design Constants (120um x 4um footprint)
    L_TOTAL = 120.0
    H_TOTAL = 4.0
    WG_WIDTH = 0.6    # Width of the waveguides
    GAP = 0.2         # Gap between waveguides in the coupling region
    
    # Segment lengths for a balanced look
    L_ARM = 10.0      # Straight input/output sections
    L_TRANS = 25.0    # Long transition zones for smooth S-curves
    L_COUPLE = 50.0   # Central interaction region
    # Verification: 10 + 25 + 50 + 25 + 10 = 120um
    
    # 2. Vertical centerline calculations
    # End spacing: centerlines at +/- 1.6 (total span 3.2 + width = 3.8um, fits in 4um)
    y_outer = 1.6
    # Coupling spacing: half the gap plus half the width
    y_inner = (GAP / 2) + (WG_WIDTH / 2)
    
    # 3. Path Construction
    # We define waypoints for the top branch. 
    # The 'smooth' function with a large radius creates the "S" shape.
    points = [
        (0, y_outer),
        (L_ARM, y_outer),
        (L_ARM + L_TRANS, y_inner),
        (L_ARM + L_TRANS + L_COUPLE, y_inner),
        (L_TOTAL - L_ARM, y_outer),
        (L_TOTAL, y_outer),
    ]
    
    # Using a very large radius (150um) ensures the corners blend into 
    # a perfectly smooth, non-linear transition that matches the target image.
    path = gf.path.smooth(points=points, radius=150.0)
    
    # 4. Cross Section Definition
    xs = gf.cross_section.cross_section(width=WG_WIDTH, layer=(1, 0))
    
    # 5. Component Assembly
    c = gf.Component("directional_coupler_smooth")
    
    # Extrude the path for the top waveguide
    top_wg = c << gf.path.extrude(path, cross_section=xs)
    
    # Create the bottom waveguide by mirroring the top
    bot_wg = c << gf.path.extrude(path, cross_section=xs)
    bot_wg.mirror_y()
    
    # Final centering for alignment
    c.movey(-c.center[1])
    c.movex(-c.center[0])
    
    return c

if __name__ == "__main__":
    # Create the component
    component = directional_coupler_final()
    
    # Export for verification
    component.write_gds("directional_coupler_final.gds")
    
    # Display the result
    component.show()