import gdsfactory as gf
import numpy as np

@gf.cell
def star_device_turn5():
    """
    Creates a 4-arm star device matching the target image.
    
    Key Features:
    - 4.7um x 4.7um footprint (Radius = 2.35um).
    - "Fat" leaf/lobe shape created by superimposing a sine wave on a linear taper.
    - Distinct straight stem section at the tips.
    - Continuous width transition from center to stem.
    """
    c = gf.Component()

    # --- 1. Define Dimensions ---
    # Constraint: Footprint 4.7um x 4.7um -> Radius = 2.35um
    R_total = 2.35
    
    # Geometry parameters estimated from target image
    L_stem = 0.55       # Length of the straight stem section
    W_stem = 0.18       # Width of the straight stem (thinner for contrast)
    W_center = 0.22     # Width at the center crossing
    W_max = 1.15        # Maximum width of the lobe (fat leaf look)
    
    L_lobe = R_total - L_stem # Length of the curved lobe section

    # --- 2. Generate Geometry Points (One Arm) ---
    # We construct the top edge profile y(x) for the arm pointing East (+x)
    N_points = 200
    x_lobe = np.linspace(0, L_lobe, N_points)
    
    # Model: y(x) = y_baseline(x) + y_sine(x)
    # This ensures the width starts at W_center and ends at W_stem smoothly
    
    # A. Linear Baseline (taper from center to stem)
    y_base = np.linspace(W_center/2, W_stem/2, N_points)
    
    # B. Sine Perturbation (creates the bulge)
    # We solve for Amplitude 'A' such that the max width is W_max.
    # The max of the sine is at x ≈ L/2 (ignoring the slight slope of baseline).
    # Approx: y_mid = (W_center + W_stem)/4 + A = W_max/2
    A = (W_max / 2) - (W_center + W_stem) / 4
    y_sine = A * np.sin(np.pi * x_lobe / L_lobe)
    
    # C. Combined Curve
    y_lobe = y_base + y_sine
    
    # D. Stem Section (Constant width)
    x_stem = np.linspace(L_lobe, R_total, 20)
    y_stem = np.full_like(x_stem, W_stem / 2)
    
    # E. Concatenate to form the full top edge
    x_all = np.concatenate([x_lobe, x_stem])
    y_all = np.concatenate([y_lobe, y_stem])
    
    # Construct the full polygon points (Top edge + Mirrored Bottom edge)
    pts_top = list(zip(x_all, y_all))
    pts_bot = list(zip(x_all[::-1], -y_all[::-1])) # Traverse back to 0, flipping Y
    points = pts_top + pts_bot
    
    # --- 3. Create Arm Component ---
    arm = gf.Component("Arm")
    arm.add_polygon(points, layer=(1, 0))
    
    # Add port at the tip for potential routing
    arm.add_port("o1", center=(R_total, 0), width=W_stem, orientation=0, layer=(1,0))

    # --- 4. Assemble the Star ---
    # Rotate and place 4 arms around the center (0,0)
    for i, angle in enumerate([0, 90, 180, 270]):
        ref = c << arm
        ref.rotate(angle)
        # Expose the ports of the references to the parent component
        c.add_port(f"o{i+1}", port=ref.ports["o1"])

    return c

# Create and save the GDS file
device = star_device_turn5()
device.write_gds("star_device_turn5.gds")