import gdsfactory as gf
import numpy as np

@gf.cell
def symmetric_coupler_final_v3():
    """
    Symmetric coupler matching the target 18x3 footprint.
    Uses manual point generation for a smooth adiabatic transition to avoid 
    potential library version conflicts.
    """
    c = gf.Component("symmetric_coupler_18x3")

    # --- 1. Define Design Parameters ---
    length = 18.0
    half_l = length / 2
    width = 0.9      # Substantial width to match visual weight
    center_gap = 0.15 # Clear but tight gap at the pinch point
    
    # Target centers to stay within +/- 1.5um vertical bounds
    # At ends: center at 1.05 (top edge at 1.05 + 0.45 = 1.5)
    y_outer = 1.05
    # At center: center at (gap/2 + width/2)
    y_inner = (center_gap / 2) + (width / 2) # 0.525 um

    # --- 2. Generate Smooth Path Points ---
    # We use a cubic smoothstep function for the transition: f(t) = 3t^2 - 2t^3
    num_points = 200
    x_vals = np.linspace(-half_l, half_l, num_points)
    
    def get_y_coord(x):
        if x < 0:
            # Left half: transition from outer to inner
            t = (x + half_l) / half_l
            return y_outer + (y_inner - y_outer) * (3 * t**2 - 2 * t**3)
        else:
            # Right half: transition from inner to outer
            t = x / half_l
            return y_inner + (y_outer - y_inner) * (3 * t**2 - 2 * t**3)

    # Compute coordinates
    y_top = np.array([get_y_coord(x) for x in x_vals])
    
    # Create Path objects (Catalog Section 3: gf.Path)
    points_top = list(zip(x_vals, y_top))
    points_bot = list(zip(x_vals, -y_top))
    
    path_top = gf.Path(points_top)
    path_bot = gf.Path(points_bot)

    # --- 3. Extrude and Build ---
    # Define the cross-section (Catalog Section 1)
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # Extrude the paths (Catalog Section 3: gf.path.extrude)
    c << gf.path.extrude(path_top, cross_section=xs)
    c << gf.path.extrude(path_bot, cross_section=xs)

    return c

if __name__ == "__main__":
    # Generate the device
    device = symmetric_coupler_final_v3()
    
    # Output file name
    gds_output = "symmetric_coupler_corrected.gds"
    device.write_gds(gds_output)
    
    print(f"GDS file saved as: {gds_output}")
    print(f"Device size: {device.dxsize:.2f} um x {device.dysize:.2f} um")