import gdsfactory as gf
import numpy as np

@gf.cell
def create_angular_interleaver():
    """
    Creates a device with two intertwined, angular paths that cross over
    multiple times, matching the target image.

    This function constructs the device by:
    1. Defining the vertices (waypoints) for the centerlines of two paths.
    2. Using straight line segments between these vertices to create sharp corners.
    3. Extruding these centerlines with a constant width to form the bands.

    The parameters are calculated to fit the target [18, 3] footprint.
    """
    c = gf.Component("angular_interleaver")

    # --- 1. Define Device Parameters from Footprint [18, 3] ---
    footprint_width = 18.0
    footprint_height = 3.0
    
    # From visual inspection, the black bands are quite thick.
    # Let's set the band width to be a significant fraction of the total height.
    band_width = 1.3

    # The centerline amplitude 'A' must be chosen so the final extruded shape
    # fits the footprint height. A simple approximation is that the total
    # height is 2 * Amplitude + band_width.
    # 3.0 = 2 * A + 1.3  =>  2 * A = 1.7  =>  A = 0.85
    amplitude = (footprint_height - band_width) / 2.0

    # Define the X-coordinates for the vertices (peaks and troughs) of the paths.
    # The component origin (0,0) will be at the center of its bounding box.
    x0 = -footprint_width / 2.0  # -9.0
    # The first feature (large diamond) is wider than the others.
    x1 = 1.0
    x2 = 5.0
    x3 = footprint_width / 2.0   # 9.0
    
    x_nodes = [x0, x1, x2, x3]

    # --- 2. Define Waypoints for the two intertwined paths ---
    
    # Path 1 starts at the top-left and alternates down, up, down.
    waypoints1 = [
        (x_nodes[0], amplitude),
        (x_nodes[1], -amplitude),
        (x_nodes[2], amplitude),
        (x_nodes[3], -amplitude),
    ]

    # Path 2 is the inverse, starting at the bottom-left and alternating up, down, up.
    waypoints2 = [
        (x_nodes[0], -amplitude),
        (x_nodes[1], amplitude),
        (x_nodes[2], -amplitude),
        (x_nodes[3], amplitude),
    ]

    # --- 3. Create Paths and Cross-Section ---
    # Using gf.Path with a list of points creates a path with sharp corners.
    # The list of waypoints is passed as a positional argument.
    path1 = gf.Path(waypoints1)
    path2 = gf.Path(waypoints2)

    # Define the cross-section used to give the paths their width.
    xs = gf.cross_section.cross_section(width=band_width)

    # --- 4. Extrude Paths and Assemble ---
    # Extrude the centerlines to create the final polygon shapes.
    shape1 = path1.extrude(cross_section=xs)
    shape2 = path2.extrude(cross_section=xs)

    # Add both shapes to the final component.
    c.add_ref(shape1)
    c.add_ref(shape2)

    return c

if __name__ == "__main__":
    # Create an instance of the device
    device = create_angular_interleaver()
    
    # Write the component to a GDSII file
    device.write_gds("angular_interleaver.gds")

    print("GDS file 'angular_interleaver.gds' has been successfully created.")

    # Optional: To visualize the component
    # device.show()