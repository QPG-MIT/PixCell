import gdsfactory as gf
import numpy as np

@gf.cell
def create_wavy_coupler():
    """
    Creates a wavy directional coupler by defining the shapes as polygons.

    This version accurately models the target image where the waveguide width
    varies and the gap between them is narrowest in the center. It achieves
    this by defining the outer boundary as a straight line and the inner
    boundary as a cosine curve.
    """
    c = gf.Component("wavy_coupler_polygon")

    # --- Parameters derived from footprint [18, 3] and image analysis ---
    length = 18.0
    total_height = 3.0
    n_points = 201

    # --- Define the boundaries for the TOP half of the device ---

    # The outer boundary is a straight horizontal line
    y_outer_val = total_height / 2  # 1.5 um

    # The inner boundary is a cosine wave: y(x) = A * cos(2*pi*x/L) + C
    # We solve for A and C based on the gap at the ends and center.
    # At x=0, L (ends): gap is ~1.0 um -> inner edge y = 1.0/2 = 0.5
    # At x=L/2 (center): gap is ~0.2 um -> inner edge y = 0.2/2 = 0.1
    #
    # System of equations:
    # y(0)   = A + C = 0.5
    # y(L/2) = -A + C = 0.1
    #
    # Solving gives: 2*C = 0.6 -> C = 0.3
    #                A = 0.5 - C -> A = 0.2
    amplitude_inner = 0.2
    offset_inner = 0.3

    # Generate the points for the boundaries
    x_coords = np.linspace(0, length, n_points)
    y_outer_coords = np.full_like(x_coords, y_outer_val)
    y_inner_coords = amplitude_inner * np.cos(2 * np.pi * x_coords / length) + offset_inner

    # Create the polygon points for the top shape by traversing the boundaries
    points_top = list(zip(x_coords, y_outer_coords)) + \
                 list(zip(np.flip(x_coords), np.flip(y_inner_coords)))

    # Add the top polygon to the component
    c.add_polygon(points_top, layer=(1, 0))

    # The bottom polygon is a mirror image of the top one across the x-axis
    points_bottom = [(px, -py) for px, py in points_top]
    c.add_polygon(points_bottom, layer=(1, 0))

    # --- Manually Add Ports ---
    # Calculate port properties at the ends (x=0 and x=length)
    end_width = y_outer_coords[0] - y_inner_coords[0]  # Should be 1.5 - 0.5 = 1.0
    port_y_top = (y_outer_coords[0] + y_inner_coords[0]) / 2  # (1.5 + 0.5)/2 = 1.0
    port_y_bottom = -port_y_top

    c.add_port(name="o1", center=(0, port_y_top), width=end_width, orientation=180, layer=(1, 0))
    c.add_port(name="o2", center=(0, port_y_bottom), width=end_width, orientation=180, layer=(1, 0))
    c.add_port(name="o3", center=(length, port_y_bottom), width=end_width, orientation=0, layer=(1, 0))
    c.add_port(name="o4", center=(length, port_y_top), width=end_width, orientation=0, layer=(1, 0))

    return c

# Main execution block for testing and saving
if __name__ == "__main__":
    wavy_coupler_device = create_wavy_coupler()
    wavy_coupler_device.show()
    wavy_coupler_device.write_gds("wavy_coupler.gds")
    print("Successfully created and saved wavy_coupler.gds with polygon-based construction.")