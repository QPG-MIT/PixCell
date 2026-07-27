import gdsfactory as gf
import numpy as np

@gf.cell
def flower_device_refined_v2():
    """
    Creates a 4-petal flower device with a 4.7um x 4.7um footprint.
    Refined parameters (v2) match the target image's slender petals and sharp, distinct tips.
    """
    c = gf.Component("flower_device_refined_v2")

    # --- Dimensions ---
    # Footprint constraint: 4.7um x 4.7um
    footprint_side = 4.7
    r_total = footprint_side / 2.0  # 2.35 um
    
    # Stub dimensions (Tips)
    # The stubs in the target are thin, short, and rectangular.
    l_stub = 0.35
    w_stub = 0.14  # Thinner width for a sharper tip appearance
    
    # Petal dimensions
    # The petal body fills the space from the center to the stub
    l_petal = r_total - l_stub
    
    # Max width of the petal
    # Reduced to 0.78 (from ~0.95) to reduce the "fat" look and match the target's aspect ratio.
    w_petal_max = 0.78 
    
    # --- Petal Shape Calculation (Sine Taper) ---
    # Profile: w(x) = w_max * sin(k * x)
    # This generates a lens-like shape that is sharp at the center and blunt at the stub interface.
    
    ratio = w_stub / w_petal_max
    
    # Calculate the phase angle (theta_end) at the stub interface.
    # We want the width to grow to w_max and then shrink back to w_stub.
    # This means theta_end must be on the falling edge of the sine wave (between pi/2 and pi).
    if ratio >= 1.0:
        theta_end = np.pi / 2
    else:
        theta_end = np.pi - np.arcsin(ratio)
    
    # Calculate spatial frequency k
    k = theta_end / l_petal
    
    # Generate high-resolution polygon points for the smooth curve
    num_points = 201
    x = np.linspace(0, l_petal, num_points)
    half_width = (w_petal_max / 2.0) * np.sin(k * x)
    
    # Create coordinate arrays for the polygon
    pts_top = np.stack([x, half_width], axis=1)
    pts_bot = np.stack([x, -half_width], axis=1)[::-1] # Reverse to trace boundary correctly
    petal_pts = np.concatenate([pts_top, pts_bot])
    
    layer = (1, 0)
    
    # --- Define Primitives ---
    
    # 1. Petal Primitive (Pointing East)
    petal = gf.Component("petal_primitive")
    petal.add_polygon(petal_pts, layer=layer)
    
    # 2. Stub Primitive (Rectangular Tip)
    stub = gf.components.rectangle(size=(l_stub, w_stub), layer=layer, centered=True)
    
    # --- Assembly ---
    # Place 4 arms rotated by 0, 90, 180, 270 degrees
    for angle in [0, 90, 180, 270]:
        # A. Place Petal
        # Rotates around (0,0), which is the start of the petal and the device center
        p_ref = c << petal
        p_ref.rotate(angle)
        
        # B. Place Stub
        # The stub connects at the end of the petal (r = l_petal).
        # Since the stub rectangle is centered, we move its center to (l_petal + l_stub/2).
        r_stub_pos = l_petal + l_stub / 2.0
        
        s_ref = c << stub
        s_ref.rotate(angle) # Rotate to align with the arm
        
        # Translate radially to the tip position
        rad = np.radians(angle)
        dx = r_stub_pos * np.cos(rad)
        dy = r_stub_pos * np.sin(rad)
        s_ref.move((dx, dy))

    # --- Center Hub ---
    # Adds a small circle at the origin to ensure all 4 petals merge into a single 
    # connected geometry, preventing potential grid-snapping gaps or rendering artifacts.
    c << gf.components.circle(radius=0.08, layer=layer)

    return c

if __name__ == "__main__":
    device = flower_device_refined_v2()
    device.write_gds("flower_device_refined_v2.gds")
    print("GDS file generated successfully.")