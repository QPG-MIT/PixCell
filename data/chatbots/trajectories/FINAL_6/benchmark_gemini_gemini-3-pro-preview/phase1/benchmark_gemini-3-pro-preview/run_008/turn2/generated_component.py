import gdsfactory as gf
import numpy as np

@gf.cell
def flower_device_corrected():
    """
    Creates a 4-petal flower device with a 4.7um x 4.7um footprint.
    Uses Ellipse primitives to ensure a smooth, convex 'lens' shape for the petals,
    fixing the previous 'diamond' shape artifact.
    """
    c = gf.Component("flower_device_corrected")

    # --- Parametric Dimensions ---
    # Footprint constraint: 4.7um x 4.7um => Radius = 2.35um
    radius_total = 2.35
    
    # Stub (Tip) Dimensions
    len_stub = 0.35
    w_stub = 0.25
    
    # Petal Geometry Calculation
    # The petal extends from the center (0,0) to the start of the stub.
    x_stub_start = radius_total - len_stub  # 2.0 um
    
    # Max width of petal (estimated from image analysis)
    w_petal_max = 1.05
    b_ellipse = w_petal_max / 2.0  # Semi-minor axis
    
    # To create a seamless joint between the petal and the stub, we calculate the
    # ellipse parameters such that at x = 2.0 (stub interface), the ellipse width 
    # exactly matches the stub width (0.25).
    # Model: Ellipse centered at x = a. Left tip at x = 0.
    # Eq: ((x_local)/a)^2 + (y/b)^2 = 1
    # We want width w_stub at distance 'x_stub_start' from the left tip.
    # x_local corresponding to x_stub_start is (x_stub_start - a).
    # Since center is at 'a', and we are 'x_stub_start' away from 0, the distance from center is |x_stub_start - a|.
    # If the ellipse is roughly centered on the arm, a ~ x_stub_start / 2.
    # We solve for 'a' (semi-major axis):
    
    half_stub_w = w_stub / 2.0
    # Ratio of height at cut point to max height
    h_ratio = half_stub_w / b_ellipse 
    
    # Based on ellipse equation solving for 'a' given the fixed cut point x_stub_start:
    # a = x_stub_start / (1 + sqrt(1 - h_ratio^2))
    term = np.sqrt(1 - h_ratio**2)
    a_ellipse = x_stub_start / (1 + term)
    
    # Ellipse dimensions
    # a_ellipse will be approx 1.015um
    
    layer = (1, 0)
    
    # --- Create Primitives ---
    # 1. Petal Shape (Ellipse)
    # Generated centered at (0,0). We will move it later.
    petal_shape = gf.components.ellipse(radii=(a_ellipse, b_ellipse), layer=layer)
    
    # 2. Stub Shape (Rectangle)
    stub_shape = gf.components.rectangle(size=(len_stub, w_stub), layer=layer, centered=True)
    
    # 3. Center Hub (Circle)
    # Adds a small solid core to ensure the 4 sharp tips merge cleanly at the center.
    hub_shape = gf.components.circle(radius=w_stub, layer=layer)
    c << hub_shape

    # --- Assembly ---
    # Rotate and place 4 arms
    for i, angle in enumerate([0, 90, 180, 270]):
        # Convert angle to radians for position calculation
        rad = np.radians(angle)
        
        # 1. Place Petal
        # The ellipse is centered at (0,0). We need to shift it so its center is at distance 'a_ellipse'
        # from the device origin, effectively placing one tip at (0,0).
        p_ref = c << petal_shape
        p_ref.rotate(angle)
        
        # Calculate radial shift vector
        dx_p = a_ellipse * np.cos(rad)
        dy_p = a_ellipse * np.sin(rad)
        p_ref.move((dx_p, dy_p))
        
        # 2. Place Stub
        # Stub center should be at x = x_stub_start + len_stub/2
        dist_stub = x_stub_start + len_stub / 2.0
        s_ref = c << stub_shape
        s_ref.rotate(angle)
        
        dx_s = dist_stub * np.cos(rad)
        dy_s = dist_stub * np.sin(rad)
        s_ref.move((dx_s, dy_s))

    return c

if __name__ == "__main__":
    device = flower_device_corrected()
    device.write_gds("flower_device_corrected.gds")
    print("GDS file generated successfully.")