import gdsfactory as gf
import numpy as np

@gf.cell
def create_sinusoidal_coupler():
    """
    Creates a device with two symmetric sinusoidal waveguides.

    The geometry is defined by creating two cosine-shaped paths that are
    mirror images of each other across the x-axis, and then extruding
    them with a constant width cross-section. This creates a device that is
    narrow in the center and wide at the ends, matching the target image.
    """
    c = gf.Component("sinusoidal_coupler_symmetric")

    # --- 1. Define Device Parameters ---
    # Parameters are re-derived based on the corrected symmetric geometry
    # to fit the 18x3 um footprint.
    # w: waveguide width, y0: average centerline offset, A: wave amplitude.
    # Total Height = 2 * (y0 + A + w/2) = 3.0
    # Middle Gap = 2*y0 - 2*A - w
    # Assuming w=1.0 and a middle gap of 0.5um leads to the values below.
    length = 18.0
    w = 1.0          # Width of each waveguide
    y0 = 0.875       # Half of the average centerline separation
    A = 0.125        # Amplitude of the sinusoidal wave
    n_points = 201   # Number of points for a smooth curve definition

    # --- 2. Generate Paths Mathematically ---
    # Create an array of x-coordinates, from -L/2 to L/2 for centering.
    x = np.linspace(-length / 2, length / 2, n_points)
    
    # The cosine term creates peaks at the ends and a trough in the middle.
    # cos_wave varies from +1 (at ends) to -1 (at center).
    cos_wave = -np.cos(2 * np.pi * x / length)
    
    # Calculate the y-coordinates for the centerlines of the two paths.
    # The bottom path is now a perfect mirror image of the top path across y=0.
    y_top_path = y0 + A * cos_wave
    y_bottom_path = -y0 - A * cos_wave  # KEY FIX: This creates the correct symmetry.

    # Create gdsfactory Path objects from the lists of points.
    path_top = gf.Path(list(zip(x, y_top_path)))
    path_bottom = gf.Path(list(zip(x, y_bottom_path)))

    # --- 3. Extrude Paths to Create Geometry ---
    # Define a cross-section with the calculated width and a target layer.
    xs = gf.cross_section.cross_section(width=w, layer=(1, 0))
    
    # Extrude the paths to create the solid waveguide components.
    band_top = gf.path.extrude(path_top, cross_section=xs)
    band_bottom = gf.path.extrude(path_bottom, cross_section=xs)

    # --- 4. Assemble the Final Component ---
    # Add the two extruded bands as references to the main component cell.
    c.add_ref(band_top)
    c.add_ref(band_bottom)
    
    return c


if __name__ == "__main__":
    # Create an instance of the component
    device = create_sinusoidal_coupler()
    
    # Write the component to a GDS file
    device.write_gds("sinusoidal_coupler.gds")
    
    print("Successfully generated sinusoidal_coupler.gds")
    # To view the component, uncomment the following line:
    # device.show()