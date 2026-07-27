import gdsfactory as gf
import numpy as np

@gf.cell
def star_device_final():
    """
    Creates a 4-arm star device using a custom sine-based polygon profile.
    
    Improvements:
    - Uses an explicit polygon equation to create a convex 'leaf' shape that 
      expands immediately from the center (fixing the pinched center issue).
    - Creates a distinct transition point between the curved lobe and the 
      straight stem (fixing the bottle-neck smoothing).
    - Matches the 4.7um x 4.7um footprint perfectly.
    """
    c = gf.Component()

    # --- 1. Define Dimensions ---
    # Constraint: Footprint 4.7um x 4.7um -> Radius = 2.35um
    R_total = 2.35
    
    # Stem: The constant-width straight section at the tip
    L_stem = 0.5
    W_stem = 0.25
    
    # Lobe: The curved leaf section
    L_lobe = R_total - L_stem  # 1.85um
    W_center = 0.25  # Width at the center crossing (matches stem)
    W_max = 0.95     # Peak width of the lobe (fat leaf)

    # --- 2. Generate Geometry Points (One Arm) ---
    # We construct the top edge profile y(x) for one arm along the +x axis.
    
    # A. Lobe Section: Sine wave superimposed on the base width
    # This creates a convex shape that angles out immediately from the center
    N_points = 100
    x_lobe = np.linspace(0, L_lobe, N_points)
    
    # y = (base_width/2) + amplitude * sin(pi * x / L)
    # At x=0, slope is positive (creates the sharp V center)
    # At x=L, slope is negative (creates the distinct stem joint)
    amplitude = (W_max - W_center) / 2
    y_lobe = (W_center / 2) + amplitude * np.sin(np.pi * x_lobe / L_lobe)
    
    # B. Stem Section: Constant width rectangle
    x_stem = np.linspace(L_lobe, R_total, 10)
    y_stem = np.ones_like(x_stem) * (W_stem / 2)
    
    # C. Combine into a closed polygon
    x_all = np.concatenate([x_lobe, x_stem])
    y_all = np.concatenate([y_lobe, y_stem])
    
    # Create list of (x,y) points: Top edge rightwards, then Bottom edge leftwards
    pts_top = list(zip(x_all, y_all))
    pts_bot = list(zip(x_all[::-1], -y_all[::-1])) # Mirror y, reverse order
    points = pts_top + pts_bot
    
    # --- 3. Create Arm Component ---
    arm = gf.Component("Arm")
    arm.add_polygon(points, layer=(1, 0))
    
    # Add port at the tip for routing
    arm.add_port("o1", center=(R_total, 0), width=W_stem, orientation=0, layer=(1,0))

    # --- 4. Assemble the Star ---
    # Rotate and place 4 arms around the center (0,0)
    for i, angle in enumerate([0, 90, 180, 270]):
        ref = c << arm
        ref.rotate(angle)
        # Expose the ports of the references
        c.add_port(f"o{i+1}", port=ref.ports["o1"])

    return c

# Create and save
device = star_device_final()
device.write_gds("star_device_final.gds")