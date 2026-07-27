import gdsfactory as gf
import numpy as np

@gf.cell
def create_sinusoidal_waveguides():
    """
    Creates a device with two intertwined, smooth sinusoidal paths,
    matching the target image.

    This function constructs the device by:
    1. Defining the parameters for a cosine wave to fit the [18, 3] footprint.
    2. Generating a dense set of points along the centerlines of two opposing
       cosine waves using numpy.
    3. Creating smooth `gf.Path` objects from these point sets.
    4. Extruding the paths with a constant width cross-section.
    """
    c = gf.Component("sinusoidal_waveguides")

    # --- 1. Define Device and Wave Parameters ---
    footprint_width = 18.0
    footprint_height = 3.0
    
    # Based on visual analysis, the two bands and the central gap are
    # of roughly equal height. Total height = 3 units -> band_width = 1.0 um.
    band_width = 1.0

    # The amplitude 'A' of the centerline is derived from the total height and band width.
    # Total Height = 2 * Amplitude + band_width
    # 3.0 = 2 * A + 1.0  =>  A = 1.0 um
    amplitude = (footprint_height - band_width) / 2.0

    # The wave completes one full cycle over the device width.
    wavelength = footprint_width  # 18.0
    
    # Wave number k = 2*pi / wavelength
    k = 2 * np.pi / wavelength

    # --- 2. Generate Points for the Centerlines ---
    # Use enough points to ensure the curve is smooth. 201 is plenty.
    num_points = 201
    
    # The component will be centered at (0,0), so x ranges from -9 to +9.
    x_coords = np.linspace(-footprint_width / 2.0, footprint_width / 2.0, num_points)

    # Top Path: A cosine wave that starts at a crest (maximum).
    # The function is A * cos(k * (x - x_start)) to shift the crest to the start.
    y_coords1 = amplitude * np.cos(k * (x_coords + footprint_width / 2.0))

    # Bottom Path: The vertical reflection of the top path.
    y_coords2 = -y_coords1

    # Combine x and y coordinates into lists of (x, y) tuples.
    waypoints1 = list(zip(x_coords, y_coords1))
    waypoints2 = list(zip(x_coords, y_coords2))

    # --- 3. Create Paths and Cross-Section ---
    # Create the Path objects from the dense waypoints.
    path1 = gf.Path(waypoints1)
    path2 = gf.Path(waypoints2)

    # Define the cross-section to give the paths their width.
    xs = gf.cross_section.cross_section(width=band_width)

    # --- 4. Extrude Paths and Assemble ---
    # Extrude the centerlines to create the final polygon shapes.
    shape1 = path1.extrude(cross_section=xs)
    shape2 = path2.extrude(cross_section=xs)

    # Add both extruded shapes as references to the final component.
    c.add_ref(shape1)
    c.add_ref(shape2)

    return c

if __name__ == "__main__":
    # Create an instance of the device
    device = create_sinusoidal_waveguides()
    
    # Write the component to a GDSII file
    device.write_gds("sinusoidal_waveguides.gds")

    print("GDS file 'sinusoidal_waveguides.gds' has been successfully created.")

    # Optional: To visualize the component
    # device.show()