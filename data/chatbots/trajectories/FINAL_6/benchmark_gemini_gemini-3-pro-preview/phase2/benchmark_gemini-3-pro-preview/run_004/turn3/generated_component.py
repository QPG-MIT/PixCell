import gdsfactory as gf
import numpy as np

@gf.cell
def device_quatrefoil_improved():
    """
    Creates a quatrefoil-shaped device with sine-tapered petals and straight stubs.
    Target footprint is 4.7um x 4.7um.
    """
    c = gf.Component()

    # --- Dimensions ---
    # Total footprint 4.7um -> Radius 2.35um
    radius_total = 2.35
    stub_len = 0.35
    petal_len = radius_total - stub_len  # 2.0 um
    
    # Widths derived from visual inspection of the target
    w_max = 0.85     # Maximum width of the petal bulge
    w_min = 0.15     # Width at the center and stub connection (matches thin stubs)
    
    layer = (1, 0)
    
    # --- 1. Generate Petal Geometry (Sine Taper) ---
    # We create a custom polygon defined by a width profile w(x).
    # A sine taper provides the smooth, convex "eye" shape.
    # Formula: w(x) = w_min + (w_max - w_min) * sin(pi * x / L)
    
    n_points = 201
    x = np.linspace(0, petal_len, n_points)
    
    # Calculate width at each point
    width_profile = w_min + (w_max - w_min) * np.sin(np.pi * x / petal_len)
    
    y_upper = width_profile / 2.0
    y_lower = -width_profile / 2.0
    
    # Construct the coordinate arrays for the polygon (Counter-Clockwise)
    # 1. Top edge: moving from x=0 to x=petal_len
    pts_top = np.column_stack((x, y_upper))
    
    # 2. Bottom edge: moving from x=petal_len back to x=0
    pts_bot = np.column_stack((np.flip(x), np.flip(y_lower)))
    
    # Combine into one array of points
    petal_pts = np.vstack((pts_top, pts_bot))
    
    # --- 2. Generate Stub Geometry ---
    # A simple rectangle extending from the tip of the petal
    # Starts at x=petal_len, width=w_min
    stub_pts = [
        (petal_len, w_min/2),
        (petal_len + stub_len, w_min/2),
        (petal_len + stub_len, -w_min/2),
        (petal_len, -w_min/2)
    ]
    
    # --- 3. Assemble Single Arm ---
    arm = gf.Component()
    arm.add_polygon(petal_pts, layer=layer)
    arm.add_polygon(stub_pts, layer=layer)
    
    # --- 4. Assemble Full Device ---
    # Rotate the arm 4 times around the center (0,0)
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)
        
    return c

if __name__ == "__main__":
    device = device_quatrefoil_improved()
    device.write_gds("quatrefoil_improved.gds")
    device.show()