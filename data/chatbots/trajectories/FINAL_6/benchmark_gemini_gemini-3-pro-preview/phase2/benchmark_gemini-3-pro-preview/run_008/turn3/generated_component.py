import gdsfactory as gf
import numpy as np

@gf.cell
def flower_device_refined():
    """
    Creates a 4-petal flower device with a 4.7um x 4.7um footprint.
    Uses a sine-taper profile for the petals to match the lens-like shape
    and sharper tips of the target image, correcting the 'fatness' of the previous ellipse approach.
    """
    c = gf.Component("flower_device_refined")

    # --- Parametric Dimensions ---
    # Footprint constraint: 4.7um x 4.7um => Radius = 2.35um
    r_total = 2.35
    
    # Stub dimensions (estimated from target image analysis)
    # The stubs in the target are distinct, thin, rectangular tips.
    l_stub = 0.38
    w_stub = 0.18
    
    # Petal dimensions
    # Petal extends from center (0,0) to the interface with the stub
    l_petal = r_total - l_stub
    
    # Max width of the petal (at its widest point)
    # Refined to match the aspect ratio of the target petals (slightly slimmer than 1.0)
    w_petal_max = 0.95 
    
    # --- Petal Shape Calculation (Sine Taper) ---
    # We construct a tapered width profile w(x) using a sine function to generate a smooth, convex 'lens' shape.
    # Profile: w(x) = w_max * sin(x * pi / L_eff)
    # 
    # Constraints:
    # 1. w(0) = 0 (Sharp point at center)
    # 2. w(l_petal) = w_stub (Seamless connection to stub)
    # 3. The petal widens to w_max and then narrows. This means the phase at x=l_petal must be > pi/2.
    
    # Solve for the phase angle at the stub interface (theta_end):
    # w(l_petal) = w_max * sin(theta_end)  =>  sin(theta_end) = w_stub / w_max
    
    ratio = w_stub / w_petal_max
    
    # Ensure ratio is valid
    if ratio >= 1.0:
        theta_end = np.pi / 2
    else:
        # Principal arcsin gives value in [0, pi/2]. 
        # We want the solution on the falling edge of the sine wave [pi/2, pi].
        theta_end = np.pi - np.arcsin(ratio)
    
    # Calculate the spatial scaling factor k
    # theta = k * x  =>  k = theta_end / l_petal
    k = theta_end / l_petal
    
    # Generate polygon points for the petal
    # High resolution ensures the curve looks smooth in GDS
    num_points = 150
    x = np.linspace(0, l_petal, num_points)
    half_width = (w_petal_max / 2.0) * np.sin(k * x)
    
    # Create coordinate arrays
    # Top edge
    pts_top = np.stack([x, half_width], axis=1)
    # Bottom edge (reversed order to trace polygon boundary correctly)
    pts_bot = np.stack([x, -half_width], axis=1)[::-1]
    
    # Combine into a single list of vertices
    petal_pts = np.concatenate([pts_top, pts_bot])
    
    layer = (1, 0)
    
    # Create the Petal Primitive Component
    # This component represents one arm pointing along the +x axis
    petal = gf.Component("petal_primitive")
    petal.add_polygon(petal_pts, layer=layer)
    
    # Create the Stub Primitive Component
    # A simple rectangle
    stub = gf.components.rectangle(size=(l_stub, w_stub), layer=layer, centered=True)
    
    # --- Assembly ---
    # Place 4 arms rotated by 0, 90, 180, 270 degrees
    for angle in [0, 90, 180, 270]:
        # 1. Place Petal
        # The petal origin is (0,0), which aligns with the device center.
        p_ref = c << petal
        p_ref.rotate(angle)
        
        # 2. Place Stub
        # The stub needs to be attached at the end of the petal.
        # Calculate the radial distance to the center of the stub.
        # Petal ends at l_petal. Stub center is l_stub/2 further out.
        r_stub_center = l_petal + l_stub / 2.0
        
        s_ref = c << stub
        s_ref.rotate(angle) # Rotate the rectangle to align with the arm angle
        
        # Move the stub radially to the tip position
        rad = np.radians(angle)
        dx = r_stub_center * np.cos(rad)
        dy = r_stub_center * np.sin(rad)
        s_ref.move((dx, dy))

    # --- Center Finish ---
    # Add a minimal center circle to ensure the four sharp tips merge into a single solid geometry
    # without varying based on grid snapping resolution.
    c << gf.components.circle(radius=0.05, layer=layer)

    return c

if __name__ == "__main__":
    device = flower_device_refined()
    device.write_gds("flower_device_refined.gds")
    print("GDS file generated successfully.")