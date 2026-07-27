import gdsfactory as gf
import numpy as np

@gf.cell
def symmetric_coupler_v4():
    """
    Symmetric coupler refined for Turn 4.
    Matches 18x3 footprint with a tighter gap and thicker waveguides.
    """
    c = gf.Component("symmetric_coupler_18x3")

    # --- 1. Define Design Parameters ---
    length = 18.0
    half_l = length / 2
    
    # Waveguide width increased for visual weight
    width = 1.0      
    
    # Central gap narrowed significantly to match target 'pinch'
    gap_center = 0.05 
    
    # Vertical centers:
    # At ends, centers at +/- 1.0um puts top/bottom edges at +/- 1.5um
    y_outer = 1.0    
    # At center, centers calculated based on the target gap
    y_inner = (gap_center / 2) + (width / 2) # 0.525 um

    # --- 2. Generate Smooth Path Points ---
    # Using a higher density of points for smooth rasterization
    num_points = 300
    x_vals = np.linspace(-half_l, half_l, num_points)
    
    def get_y_coord(x):
        # Normalize x to [0, 1] relative to the half-length
        t = abs(x) / half_l
        # Cubic smoothstep: 3t^2 - 2t^3 
        # This provides zero-velocity transitions at center and ports
        f_t = 3 * (t**2) - 2 * (t**3)
        # Interpolate between inner (center) and outer (end) positions
        return y_inner + (y_outer - y_inner) * f_t

    # Compute path coordinates
    y_top = np.array([get_y_coord(x) for x in x_vals])
    
    # Create GDSFactory Paths (Catalog Section 3)
    path_top = gf.Path(list(zip(x_vals, y_top)))
    path_bot = gf.Path(list(zip(x_vals, -y_top)))

    # --- 3. Extrude and Assemble ---
    # Define cross-section (Catalog Section 1)
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # Extrude (Catalog Section 3: gf.path.extrude)
    c << gf.path.extrude(path_top, cross_section=xs)
    c << gf.path.extrude(path_bot, cross_section=xs)

    return c

if __name__ == "__main__":
    # Generate the device
    device = symmetric_coupler_v4()
    
    # Save GDS
    device.write_gds("symmetric_coupler_v4.gds")
    
    print(f"Device size: {device.dxsize:.2f} um x {device.dysize:.2f} um")
    # Expected Output: 18.00 um x 3.00 um