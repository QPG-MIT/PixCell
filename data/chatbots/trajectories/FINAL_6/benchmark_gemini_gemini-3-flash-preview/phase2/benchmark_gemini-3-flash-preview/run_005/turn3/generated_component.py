import gdsfactory as gf
import numpy as np

def get_bezier_points(p0, p1, p2, p3, n=100):
    """Generates points for a cubic Bezier curve."""
    t = np.linspace(0, 1, n)
    # Cubic Bezier formula: (1-t)^3*P0 + 3(1-t)^2*t*P1 + 3(1-t)*t^2*P2 + t^3*P3
    points = (1-t)[:, None]**3 * p0 + \
             3*(1-t)[:, None]**2 * t[:, None] * p1 + \
             3*(1-t)[:, None] * t[:, None]**2 * p2 + \
             t[:, None]**3 * p3
    return points

@gf.cell
def recreate_cross_device_v4():
    """
    Recreates the 4-lobed cross device with custom Bezier petals.
    Footprint constraint: 4.7um x 4.7um.
    """
    layer = (1, 0)
    
    # --- 1. Dimensions (Total span 4.7um -> Radius 2.35um) ---
    total_radius = 2.35
    tip_length = 0.45      # Length of the rectangular tip
    petal_len = total_radius - tip_length
    
    max_petal_width = 1.05 # Thickness of the "leaf"
    tip_width = 0.22       # Width of the rectangular end
    base_width = 0.50      # Width at center to ensure a solid junction

    # --- 2. Create the Arm (Petal + Tip) ---
    arm = gf.Component("arm_template")

    # Define Bezier control points for the top profile of the petal
    p0 = np.array([0, base_width / 2])
    p1 = np.array([petal_len * 0.3, max_petal_width / 2 * 1.2]) # Bulge
    p2 = np.array([petal_len * 0.7, max_petal_width / 2 * 0.9]) # Taper start
    p3 = np.array([petal_len, tip_width / 2])                  # Connection to tip

    top_half = get_bezier_points(p0, p1, p2, p3)
    bottom_half = top_half[::-1] * [1, -1] # Mirror vertically and reverse order
    petal_poly = np.concatenate([top_half, bottom_half])
    
    arm.add_polygon(petal_poly, layer=layer)

    # Add the rectangular tip
    rect_tip = gf.components.rectangle(size=(tip_length, tip_width), layer=layer, centered=True)
    t_ref = arm << rect_tip
    t_ref.movex(petal_len + tip_length / 2)

    # --- 3. Assemble and Merge ---
    assembly = gf.Component("assembly_temp")
    for angle in [0, 90, 180, 270]:
        ref = assembly << arm
        ref.rotate(angle)

    # Boolean OR to create a single solid silhouette (unifies the center)
    # We use a dummy boolean on the assembly itself to flatten it into one shape
    final_comp = gf.boolean(A=assembly, B=assembly, operation="or", layer=layer)
    
    return final_comp

if __name__ == "__main__":
    # Generate and verify
    device = recreate_cross_device_v4()
    
    w, h = device.dxsize, device.dysize
    print(f"Verified Footprint: {w:.3f} um x {h:.3f} um")
    
    # Output
    device.write_gds("cross_device_v4.gds")
    device.show()