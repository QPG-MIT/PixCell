import gdsfactory as gf
import numpy as np

def get_bezier_points(p0, p1, p2, p3, n=100):
    """Generates points for a cubic Bezier curve for smooth parametric shapes."""
    t = np.linspace(0, 1, n)
    # Cubic Bezier formula: (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
    points = (1-t)[:, None]**3 * p0 + \
             3*(1-t)[:, None]**2 * t[:, None] * p1 + \
             3*(1-t)[:, None] * t[:, None]**2 * p2 + \
             t[:, None]**3 * p3
    return points

@gf.cell
def recreate_cross_device_v5():
    """
    Recreates the 4-lobed cross device with refined Bezier petals.
    Footprint constraint: 4.7um x 4.7um.
    """
    layer = (1, 0)
    
    # --- 1. Dimensions (Total span 4.7um -> Max Radius 2.35um) ---
    total_radius = 2.35
    tip_length = 0.55      # Lengthened slightly for better proportion
    tip_width = 0.16       # Thinned to match target
    petal_len = total_radius - tip_length
    
    max_petal_width = 0.88 # Slightly narrower than v4 for an elongated look
    base_width = 0.42      # Provides a solid central junction

    # --- 2. Create the Arm (Petal + Tip) ---
    arm = gf.Component("arm_template")

    # Define Bezier control points for the top profile
    # p0: Start at center junction
    # p1: Control the 'bulge' location and height
    # p2: Control the taper down to the tip
    # p3: End at the connection to the rectangular tip
    p0 = np.array([0, base_width / 2])
    p1 = np.array([petal_len * 0.35, max_petal_width / 2]) 
    p2 = np.array([petal_len * 0.8, max_petal_width / 2 * 0.6])
    p3 = np.array([petal_len, tip_width / 2])

    top_half = get_bezier_points(p0, p1, p2, p3)
    bottom_half = top_half[::-1] * [1, -1] # Mirror and reverse for a closed polygon
    petal_poly = np.concatenate([top_half, bottom_half])
    
    arm.add_polygon(petal_poly, layer=layer)

    # Add the rectangular tip
    rect_tip = gf.components.rectangle(size=(tip_length, tip_width), layer=layer, centered=True)
    t_ref = arm << rect_tip
    t_ref.movex(petal_len + tip_length / 2)

    # --- 3. Assemble and Merge ---
    assembly = gf.Component("assembly")
    for angle in [0, 90, 180, 270]:
        ref = assembly << arm
        ref.rotate(angle)

    # Perform a Boolean OR to merge the 4 arms into a single continuous shape
    # This ensures the center is a solid unified polygon.
    final_comp = gf.boolean(A=assembly, B=assembly, operation="or", layer=layer)
    
    return final_comp

if __name__ == "__main__":
    # Generate the component
    device = recreate_cross_device_v5()
    
    # Verify footprint constraints
    w, h = device.dxsize, device.dysize
    print(f"Verified Footprint: {w:.3f} um x {h:.3f} um (Target: 4.7 x 4.7)")
    
    # Export and visualize
    device.write_gds("cross_device_v5.gds")
    device.show()