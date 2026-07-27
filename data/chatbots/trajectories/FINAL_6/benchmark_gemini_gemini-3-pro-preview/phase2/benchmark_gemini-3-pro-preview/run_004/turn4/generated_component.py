import gdsfactory as gf
import numpy as np

@gf.cell
def device_quatrefoil_improved_v2():
    """
    Creates a quatrefoil-shaped device with sine-tapered petals and straight stubs.
    Target footprint is 4.7um x 4.7um.
    Includes adjustments for petal 'fullness' and cleaner polygon construction.
    """
    c = gf.Component()

    # --- Dimensions ---
    # Total footprint 4.7um -> Radius 2.35um
    radius_total = 2.35
    stub_len = 0.3       
    petal_len = radius_total - stub_len  # 2.05 um
    
    # Widths 
    # Increased w_max to match the "chubby" look of the target petals
    w_max = 1.0          
    # Slightly increased w_min for better visibility/manufacturability 
    # and to match the visual weight of the stubs in the target
    w_min = 0.2          
    
    layer = (1, 0)
    
    # --- 1. Generate Geometry Points ---
    
    # -- Petal Section (Sine Taper) --
    # Formula: w(x) = w_min + (w_max - w_min) * sin(pi * x / L)
    # This creates the smooth convex "eye" shape of the petal.
    n_points = 201
    x_petal = np.linspace(0, petal_len, n_points)
    width_profile = w_min + (w_max - w_min) * np.sin(np.pi * x_petal / petal_len)
    
    y_upper_petal = width_profile / 2.0
    
    # Top chain: Sine curve from center (x=0) to petal end (x=petal_len)
    chain_top = np.column_stack((x_petal, y_upper_petal))
    
    # Stub chain: Rectangular extension
    # Draws the box at the tip: 
    # (petal_len, w_min/2) -> (radius_total, w_min/2) -> (radius_total, -w_min/2) -> (petal_len, -w_min/2)
    # Note: The first point connects automatically from the end of chain_top
    chain_stub = np.array([
        [radius_total, w_min/2.0],
        [radius_total, -w_min/2.0],
        [petal_len, -w_min/2.0]
    ])
    
    # Bottom chain: Sine curve from petal end back to center
    # We flip the arrays to travel from x=petal_len back to x=0
    chain_bot = np.column_stack((np.flip(x_petal), -np.flip(y_upper_petal)))
    
    # Concatenate all points into one ordered polygon ring (Counter-Clockwise)
    arm_pts = np.vstack((chain_top, chain_stub, chain_bot))
    
    # --- 2. Assemble Full Device ---
    # Create the single arm component
    arm = gf.Component()
    arm.add_polygon(arm_pts, layer=layer)
    
    # Rotate the arm 4 times around the center (0,0) to form the cross
    for angle in [0, 90, 180, 270]:
        ref = c << arm
        ref.rotate(angle)
        
    return c

if __name__ == "__main__":
    device = device_quatrefoil_improved_v2()
    device.write_gds("quatrefoil_improved_v2.gds")
    device.show()