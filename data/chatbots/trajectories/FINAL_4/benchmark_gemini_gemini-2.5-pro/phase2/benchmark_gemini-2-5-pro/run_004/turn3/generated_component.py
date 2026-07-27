import gdsfactory as gf
import numpy as np

@gf.cell
def create_sinusoidal_coupler():
    """
    Creates a device with two parallel sinusoidal waveguides.

    The geometry is defined by creating two cosine-shaped paths and extruding
    them with a constant width cross-section. This approach correctly models the
    target image, which has a constant width for the waveguides and the gap.
    """
    c = gf.Component("sinusoidal_coupler")

    # --- 1. Define Device Parameters ---
    # Parameters are derived from the 18x3 um footprint and visual inspection.
    # See design notes in the thought process for the derivation.
    length = 18.0
    w = 1.0         # Width of each waveguide band
    y0 = 1.0        # Vertical offset of the centerlines from the x-axis
    A = 0.25        # Amplitude of the sinusoidal wave
    n_points = 201  # Number of points for a smooth curve definition

    # --- 2. Generate Paths Mathematically ---
    # Create an array of x-coordinates, from -L/2 to L/2 for centering.
    x = np.linspace(-length / 2, length / 2, n_points)
    
    # The cosine term creates a trough at the ends and a peak in the middle.
    # We use `-cos(...)` to get peaks at the ends and a trough in the middle.
    cos_wave = -np.cos(2 * np.pi * x / length)
    
    # Calculate the y-coordinates for the centerlines of the two paths.
    # The device's natural center is at y=A. We subtract A to center it at y=0.
    y_top_path = y0 + A * cos_wave - A
    y_bottom_path = -y0 + A * cos_wave - A

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