import gdsfactory as gf
import numpy as np

@gf.cell
def create_device():
    """
    Recreates the specified device geometry using gdsfactory.

    The construction uses a boolean combination of primitive shapes:
    - An outer ring made from two ellipses.
    - Two inner bars made from rectangles with rectangular holes.
    - Four connecting arms made from rotated and mirrored tapers.
    - A final boolean union merges all parts into a single component.
    """
    c = gf.Component("complex_device")

    # Define a common layer for all operations
    layer = (1, 0)

    # 1. Define device parameters based on footprint and visual inspection
    # Footprint from constraint: width=5.5 um, height=3.0 um
    total_width = 5.5
    total_height = 3.0
    ring_thickness = 0.4

    # Parameters for the inner horizontal bars
    bar_height = 0.5
    bar_gap = 0.7
    bar_length = 2.4  # Length of the straight central section
    bar_y_offset = (bar_gap + bar_height) / 2.0  # Vertical position of bar centers

    # Parameters for the rectangular holes inside the bars
    hole_width = 0.5
    hole_height = 0.3
    hole_spacing = 0.3  # Space between the two holes
    hole_x_offset = (hole_spacing + hole_width) / 2.0

    # 2. Create the outer ring
    radii_outer = (total_width / 2.0, total_height / 2.0)
    radii_inner = (radii_outer[0] - ring_thickness, radii_outer[1] - ring_thickness)

    outer_ellipse = gf.components.ellipse(radii=radii_outer, layer=layer)
    inner_ellipse = gf.components.ellipse(radii=radii_inner, layer=layer)
    ring = gf.boolean(A=outer_ellipse, B=inner_ellipse, operation="not", layer=layer)

    # 3. Create the inner bars with holes
    # First, define a single bar component using a boolean 'not'
    bar_body = gf.components.rectangle(size=(bar_length, bar_height), centered=True, layer=layer)

    # FIX: Create the hole primitive at the origin first.
    hole_primitive = gf.components.rectangle(
        size=(hole_width, hole_height), centered=True, layer=layer
    )
    # FIX: Then, create two moved versions of the hole component.
    hole1 = hole_primitive.copy().move(destination=(-hole_x_offset, 0))
    hole2 = hole_primitive.copy().move(destination=(hole_x_offset, 0))

    single_bar = gf.boolean(A=bar_body, B=[hole1, hole2], operation="not", layer=layer)

    # Create and position the top and bottom bars
    bar_top = single_bar.copy().movey(bar_y_offset)
    bar_bottom = single_bar.copy().movey(-bar_y_offset)

    # 4. Create the four connecting arms using tapers
    # Calculate geometry for the top-right arm taper
    p_start = (bar_length / 2, bar_y_offset)
    y_conn = bar_y_offset + 0.2  # Connect slightly above the bar's centerline
    # Calculate x-position on the inner ellipse for the given y
    x_conn = radii_inner[0] * (1 - (y_conn / radii_inner[1]) ** 2) ** 0.5
    p_end = (x_conn, y_conn)

    delta_x = p_end[0] - p_start[0]
    delta_y = p_end[1] - p_start[1]
    taper_length = (delta_x**2 + delta_y**2) ** 0.5
    taper_angle_deg = np.rad2deg(np.arctan2(delta_y, delta_x))

    # Define the taper primitive
    arm_taper = gf.components.taper(
        length=taper_length, width1=bar_height, width2=bar_height + 0.1, layer=layer
    )

    # Create, transform, and position the four arms
    arm_tr = arm_taper.copy().rotate(taper_angle_deg).move(p_start)
    arm_tl = arm_taper.copy().mirror_y().rotate(taper_angle_deg).move((-p_start[0], p_start[1]))
    arm_br = arm_taper.copy().mirror_x().rotate(-taper_angle_deg).move((p_start[0], -p_start[1]))
    arm_bl = arm_taper.copy().mirror().rotate(-taper_angle_deg).move((-p_start[0], -p_start[1]))

    # 5. Final Assembly: Union all parts with a boolean 'or'
    # The boolean function can take a list of components as the first argument
    final_device_geo = gf.boolean(
        A=[ring, bar_top, bar_bottom, arm_tr, arm_tl, arm_br, arm_bl],
        operation="or",
        layer=layer,
    )

    # Add the final combined geometry to the component
    c.add_ref(final_device_geo)

    return c

if __name__ == "__main__":
    # Instantiate the component
    device = create_device()
    # Show the component in the KLayout viewer
    device.show()