import numpy as np
import gdsfactory as gf

@gf.cell
def symmetric_coupler_bezier_v5_fixed():
    """
    Turn 5 (Fixed): Corrected broadcasting for manual Bezier calculation.
    Optimized parameters for visual matching with target image.
    Footprint: 18um x 3um.
    """
    c = gf.Component("symmetric_coupler_v5")
    
    # 1. Design Parameters
    length = 18.0
    total_height = 3.0
    width = 1.1      # Wider for better visual match
    gap = 0.1        # Gap at the center
    
    # 2. Coordinate Calculations
    # At ports: centerline = 1.5 - (width/2) = 0.95
    # At center: centerline = (gap/2) + (width/2) = 0.05 + 0.55 = 0.6
    y_end = 0.95
    y_mid = 0.6
    
    # 3. Manual Bezier Curve Calculation
    # Control points (P0 to P5) for a 5th degree Bezier curve
    cp = [
        (0.0, y_end),      # P0: Start
        (5.0, y_end),      # P1: Keep start horizontal
        (7.5, y_mid),      # P2: Approach center
        (10.5, y_mid),     # P3: Exit center
        (13.0, y_end),     # P4: Return to horizontal
        (18.0, y_end)      # P5: End
    ]
    
    num_points = 200
    # Reshape t to (200, 1) for broadcasting with (2,) coordinates
    t = np.linspace(0, 1, num_points)[:, np.newaxis]
    
    # Bernstein basis polynomials for n=5
    b0 = 1 * (1-t)**5
    b1 = 5 * t * (1-t)**4
    b2 = 10 * t**2 * (1-t)**3
    b3 = 10 * t**3 * (1-t)**2
    b4 = 5 * t**4 * (1-t)
    b5 = 1 * t**5
    
    # Vectorized point calculation
    path_points = (
        b0 * np.array(cp[0]) +
        b1 * np.array(cp[1]) +
        b2 * np.array(cp[2]) +
        b3 * np.array(cp[3]) +
        b4 * np.array(cp[4]) +
        b5 * np.array(cp[5])
    )
    
    # 4. Path and Component Construction
    path = gf.Path(path_points)
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))
    
    # Add Arms
    top_arm = c << gf.path.extrude(path, cross_section=xs)
    bot_arm = c << gf.path.extrude(path, cross_section=xs)
    bot_arm.mirror_y()
    
    # 5. Define Ports
    # extrude() automatically creates 'o1' at start and 'o2' at end
    c.add_port("o1", port=top_arm.ports["o1"])
    c.add_port("o2", port=bot_arm.ports["o1"])
    c.add_port("o3", port=top_arm.ports["o2"])
    c.add_port("o4", port=bot_arm.ports["o2"])
    
    return c

if __name__ == "__main__":
    # Create the component
    component = symmetric_coupler_bezier_v5_fixed()
    
    # Verify exact footprint
    bbox = component.dbbox()
    print(f"Final device dimensions: {bbox.width():.2f}um x {bbox.height():.2f}um")
    
    # Save and show
    component.write_gds("symmetric_coupler_v5.gds")
    component.show()