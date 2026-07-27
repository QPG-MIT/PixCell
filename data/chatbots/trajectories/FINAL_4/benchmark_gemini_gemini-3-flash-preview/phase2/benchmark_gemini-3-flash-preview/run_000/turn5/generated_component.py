import gdsfactory as gf
import numpy as np

@gf.cell
def symmetric_coupler_v5():
    """
    Symmetric coupler refined for Turn 5.
    Uses a sine-squared profile for a smoother adiabatic transition.
    Adjusted width and gap for a clearer 'pinch' that matches the target image.
    """
    c = gf.Component("symmetric_coupler_18x3")

    # --- 1. Define Design Parameters ---
    # Total footprint: 18um x 3um
    length = 18.0
    half_l = length / 2
    
    # Waveguide width reduced to create more visual 'breathing room'
    # 0.7um provides a bold look without overwhelming the gap
    width = 0.7      
    
    # Central gap increased to be clearly visible in low-res rasters
    gap_center = 0.2 
    
    # Vertical centers (y-coordinates):
    # At the ends, we place centers at +/- 1.1um.
    # Top edge: 1.1 + 0.35 = 1.45 (just inside the 1.5um boundary)
    y_outer = 1.1    
    
    # At the center, centers are calculated based on the gap
    # y_inner = (gap/2) + (width/2)
    y_inner = (gap_center / 2) + (width / 2) # 0.1 + 0.35 = 0.45

    # --- 2. Generate Smooth Path Points ---
    # We use a sin^2 profile across the entire length:
    # y(x) = y_inner + (y_outer - y_inner) * sin^2(pi * x / length)
    # This ensures y(-9) = y_outer, y(0) = y_inner, and y(9) = y_outer
    # and that the slope is 0 at all three critical points.
    
    num_points = 400
    x_vals = np.linspace(-half_l, half_l, num_points)
    
    # Compute the top waveguide path
    y_top = y_inner + (y_outer - y_inner) * (np.sin(np.pi * x_vals / length)**2)
    
    # Create GDSFactory Paths (Catalog Section 3)
    path_top = gf.Path(list(zip(x_vals, y_top)))
    path_bot = gf.Path(list(zip(x_vals, -y_top)))

    # --- 3. Extrude and Assemble ---
    # Define cross-section (Catalog Section 1)
    xs = gf.cross_section.cross_section(width=width, layer=(1, 0))

    # Extrude the paths into geometry (Catalog Section 3)
    c << gf.path.extrude(path_top, cross_section=xs)
    c << gf.path.extrude(path_bot, cross_section=xs)

    return c

if __name__ == "__main__":
    # Generate the device
    device = symmetric_coupler_v5()
    
    # Save GDS for inspection
    device.write_gds("symmetric_coupler_v5.gds")
    
    # Verify footprint
    print(f"Device size: {device.dxsize:.2f} um x {device.dysize:.2f} um")
    # Output should be approx 18.00 um x 2.90 um (well within the 18x3 constraint)