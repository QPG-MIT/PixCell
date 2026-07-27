import gdsfactory as gf
import numpy as np

@gf.cell
def symmetric_coupler_reconstructed():
    """
    Recreates the symmetric coupler using a smooth parametric path.
    Utilizes gf.Path and gf.path.extrude from the catalog.
    """
    c = gf.Component("symmetric_coupler_18x3")

    # --- 1. Define Visual Parameters ---
    # We use a larger width and smaller gap to match the "bold" look of the image.
    length = 18.0
    height = 3.0
    wg_width = 1.0   # Substantial width to match visual weight
    center_gap = 0.1 # Tight gap at the pinch point

    # --- 2. Calculate Vertical Bounds ---
    # Center y-coord at ends (touches +/- 1.5um footprint edge)
    y_outer = (height / 2) - (wg_width / 2)  # 1.0 um
    # Center y-coord at middle (pinch point)
    y_inner = (center_gap / 2) + (wg_width / 2) # 0.55 um

    # --- 3. Generate Smooth Parametric Paths ---
    # We generate a list of points using a cosine function for an adiabatic transition.
    # Formula: y = avg_y + (amplitude) * cos(pi * x / half_length)
    num_points = 101
    x = np.linspace(-length/2, length/2, num_points)
    
    # Calculate y-coordinates for the top path
    y_avg = (y_outer + y_inner) / 2
    y_amp = (y_inner - y_outer) / 2
    y_top = y_avg + y_amp * np.cos(np.pi * x / (length / 2))

    # Create Path objects as per Catalog Section 3
    points_top = list(zip(x, y_top))
    points_bottom = list(zip(x, -y_top))
    
    path_top = gf.Path(points_top)
    path_bottom = gf.Path(points_bottom)

    # --- 4. Extrude Paths into Geometry ---
    # Define the cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Extrude the paths into components (Catalog Section 3: gf.path.extrude)
    top_wg = c << gf.path.extrude(path_top, cross_section=xs)
    bot_wg = c << gf.path.extrude(path_bottom, cross_section=xs)

    return c

if __name__ == "__main__":
    # Create the component
    device = symmetric_coupler_reconstructed()
    
    # Save to GDS (ensure the file is actually produced)
    gds_filename = "symmetric_coupler_final.gds"
    device.write_gds(gds_filename)
    
    # Print verification info
    print(f"GDS file successfully generated: {gds_filename}")
    print(f"Footprint Verification: {device.dxsize:.1f} um x {device.dysize:.1f} um")