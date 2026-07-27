import gdsfactory as gf
import numpy as np

@gf.cell
def create_intertwined_waveguides():
    """
    Creates a device with two intertwined, crossing sinusoidal paths,
    matching the target image.

    This function constructs the device by:
    1. Defining parameters for a sine wave completing 1.5 cycles over
       the 18um device width.
    2. Calculating amplitude and width such that they are equal (A=w=1.0) and
       satisfy the 3um total height constraint (2*A + w = 3).
    3. Generating points for two opposing sine waves (y and -y) to create
       the crossing pattern.
    4. Creating smooth `gf.Path` objects from these points.
    5. Extruding the paths with a constant width cross-section.
    6. Centering the final component at the origin.
    """
    c = gf.Component("intertwined_waveguides")

    # --- 1. Define Device and Wave Parameters ---
    footprint_width = 18.0
    footprint_height = 3.0 # This is a design constraint.
    num_cycles = 1.5

    # From visual analysis and dimensional constraints:
    # The total vertical extent is determined by the wave's amplitude (A) and
    # the band's width (w): footprint_height = 2*A + w.
    # The central "eye" opening has a maximum height of: max_gap = 2*A - w.
    # Visually, the band width appears equal to this max_gap: w = 2*A - w.
    # This simplifies to 2*w = 2*A, or A = w.
    # Substituting back into the height constraint: 2*w + w = 3.0 => 3*w = 3.0
    band_width = 1.0
    amplitude = 1.0

    # The wave completes 1.5 cycles over the device width.
    wavelength = footprint_width / num_cycles  # 18.0 / 1.5 = 12.0
    
    # Wave number k = 2*pi / wavelength
    k = 2 * np.pi / wavelength

    # --- 2. Generate Points for the Centerlines ---
    # Use enough points to ensure the curve is smooth and accurate.
    num_points = 401
    
    # Generate x-coordinates from 0 to the full width. This allows a simple
    # sin() function to naturally start and end at y=0 over 1.5 cycles.
    x_coords = np.linspace(0, footprint_width, num_points)

    # Path 1: A simple sine wave.
    y_coords1 = amplitude * np.sin(k * x_coords)

    # Path 2: The vertical reflection of the first path.
    y_coords2 = -y_coords1

    # Combine x and y coordinates into lists of (x, y) tuples for gdsfactory.
    waypoints1 = list(zip(x_coords, y_coords1))
    waypoints2 = list(zip(x_coords, y_coords2))

    # --- 3. Create Paths and Cross-Section ---
    path1 = gf.Path(waypoints1)
    path2 = gf.Path(waypoints2)
    xs = gf.cross_section.cross_section(width=band_width)

    # --- 4. Extrude Paths and Assemble ---
    shape1 = path1.extrude(cross_section=xs)
    shape2 = path2.extrude(cross_section=xs)
    c.add_ref(shape1)
    c.add_ref(shape2)
    
    # --- 5. Center the Component ---
    # The component is currently drawn with its bottom-left corner near the
    # origin. We move it to be centered at (0, 0).
    cx, cy = c.center
    c.move((-cx, -cy))

    return c

if __name__ == "__main__":
    # Create an instance of the device
    device = create_intertwined_waveguides()
    
    # Write the component to a GDSII file
    device.write_gds("intertwined_waveguides.gds")

    print("GDS file 'intertwined_waveguides.gds' has been successfully created.")

    # Optional: To visualize the component
    # device.show()