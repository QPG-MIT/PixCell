import gdsfactory as gf
import numpy as np


def create_component() -> gf.Component:
    """
    Creates the target component by constructing the two symmetrical halves as
    polygons and then adding them to a component.

    This approach is chosen because the shape has straight outer boundaries
    and complex, smooth inner boundaries, which is difficult to achieve with
    standard primitives or simple boolean operations. Building the polygons
    directly from a calculated path provides full control over the final shape.
    """

    # --- 1. Define Geometric Parameters ---
    # These parameters are estimated from the target image and constraints.
    width_total = 120.0
    height_total = 24.0  # Increased height to better match the visual aspect ratio
    length_straight = 50.0
    gap = 1.5  # Increased gap to better match the visual
    layer_spec = (1, 0) # Define the layer to be used for geometry and ports

    # y-coordinate of the inner curve at the port (the tip of the "diamond" void)
    # This value is chosen to create a visually appealing curve.
    y_port_inner = 8.0

    # The radius for the gf.path.smooth function, controlling bend curvature.
    bend_radius = 15.0

    # --- 2. Create the Main Component ---
    c = gf.Component("custom_coupler_via_polygon")

    # --- 3. Define the Path for the Inner Boundary of the Top Half ---
    # The path is defined by key waypoints and smoothed automatically.
    x_port_left = -width_total / 2
    x_straight_left = -length_straight / 2
    x_straight_right = length_straight / 2
    x_port_right = width_total / 2

    y_center_inner = gap / 2

    # Waypoints for the smooth path generator
    points = [
        (x_port_left, y_port_inner),
        (x_straight_left, y_center_inner),
        (x_straight_right, y_center_inner),
        (x_port_right, y_port_inner),
    ]

    # Generate the smooth path object
    inner_boundary_path = gf.path.smooth(points, radius=bend_radius)

    # --- 4. Construct the Polygon for the Top Half ---
    # Get the points from the generated smooth path
    path_points = inner_boundary_path.points

    # Define the corners of the outer rectangular boundary
    corner_top_right = (x_port_right, height_total / 2)
    corner_top_left = (x_port_left, height_total / 2)

    # Combine the path points and corner points to form a closed polygon.
    # The list of points must be ordered to trace the boundary.
    # We use the path points as they are, then add the top corners in reverse
    # order (right then left) to close the loop.
    top_poly_points = np.concatenate(
        [path_points, [corner_top_right, corner_top_left]]
    )

    # Add the polygon to the component, specifying the layer
    c.add_polygon(top_poly_points, layer=layer_spec)

    # --- 5. Construct the Polygon for the Bottom Half ---
    # This is a mirror image of the top half across the x-axis.
    # We can create it by simply negating the y-coordinates of the top polygon.
    bottom_poly_points = top_poly_points * np.array([1, -1])

    # Add the second polygon to the component, specifying the layer
    c.add_polygon(bottom_poly_points, layer=layer_spec)

    # --- 6. Add Ports ---
    # The ports are defined on the vertical edges at the left and right.
    port_height = height_total / 2 - y_port_inner
    port_y_center_top = (height_total / 2 + y_port_inner) / 2
    port_y_center_bot = -port_y_center_top

    c.add_port(
        name="o1",
        center=(x_port_left, port_y_center_bot),
        width=port_height,
        orientation=180,
        layer=layer_spec,
    )
    c.add_port(
        name="o2",
        center=(x_port_left, port_y_center_top),
        width=port_height,
        orientation=180,
        layer=layer_spec,
    )
    c.add_port(
        name="o3",
        center=(x_port_right, port_y_center_top),
        width=port_height,
        orientation=0,
        layer=layer_spec,
    )
    c.add_port(
        name="o4",
        center=(x_port_right, port_y_center_bot),
        width=port_height,
        orientation=0,
        layer=layer_spec,
    )

    return c


if __name__ == "__main__":
    # Instantiate the component by calling the creation function
    my_component = create_component()

    # Write the component to a GDS file in the current directory
    my_component.write_gds("final_coupler.gds")

    # To visualize the component, you can uncomment the line below
    # my_component.show()