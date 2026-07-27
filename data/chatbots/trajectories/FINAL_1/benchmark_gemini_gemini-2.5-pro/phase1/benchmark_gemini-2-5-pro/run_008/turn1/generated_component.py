import gdsfactory as gf
from gdsfactory.path import extrude_transition, transition
from gdsfactory.cross_section import cross_section
# Corrected import: The bezier function generates points, not a Path object directly.
from gdsfactory.path.points import bezier as bezier_points

@gf.cell
def create_device():
    """
    Creates a Y-splitter component by assembling three parametrically defined shapes:
    a central tapering spike and two curved, tapering outer arms. This approach
    matches the visual representation of three distinct but contiguous shapes at
    the input, which smoothly separate into the two outputs.
    """
    c = gf.Component()

    # Define device parameters based on the footprint [40.0, 1.7] um.
    device_length = 40.0
    device_height = 1.7

    # Define waveguide and geometric properties based on visual inspection.
    output_wg_width = 0.5
    # The total input width appears to be a standard waveguide width.
    input_total_width = 0.5

    # Apportion the input width between the central spike and the two outer arms.
    # This ratio is chosen to match the visual appearance.
    arm_width_start = 0.15
    spike_width_start = input_total_width - 2 * arm_width_start  # 0.5 - 2*0.15 = 0.2 um

    # The central spike tapers to a sharp point. Its length is a design choice.
    spike_length = 15.0
    spike_width_end = 0.01  # A very small width to approximate a sharp tip.

    # --- 1. Create the central tapering spike ---
    # The `taper` primitive is used for this part.
    spike = gf.components.taper(
        length=spike_length,
        width1=spike_width_start,
        width2=spike_width_end,
    )
    # Add the spike to the component, centered on the y-axis at the origin.
    c.add_ref(spike)

    # --- 2. Create the outer arms using path extrusion ---
    # Calculate the start and end y-coordinates for the centerline of the top arm.
    # The arms and spike are touching at the input (gap=0).
    y_center_start = (spike_width_start / 2) + (arm_width_start / 2)
    # The output y-center is determined by the total device height and output waveguide width.
    y_center_end = (device_height - output_wg_width) / 2

    # Define the path for the arm's centerline.
    # A Bezier curve provides a smooth transition with horizontal tangents at start and end.
    dx = device_length
    dy = y_center_end - y_center_start  # The total vertical displacement of the arm
    
    control_points = [
        (0, 0),        # Start point (relative to its final position)
        (dx / 2, 0),   # Control point for horizontal start tangent
        (dx / 2, dy),  # Control point for horizontal end tangent
        (dx, dy),      # End point (relative)
    ]
    
    # CORRECTED PATH CREATION:
    # 1. Generate the array of points using the imported bezier_points function.
    points = bezier_points(control_points=control_points, npoints=201)
    # 2. Create a Path object from the generated points.
    arm_path = gf.Path(points)

    # Define the width transition (taper) along the path.
    xs_start = cross_section(width=arm_width_start)
    xs_end = cross_section(width=output_wg_width)
    width_transition = transition(
        cross_section1=xs_start,
        cross_section2=xs_end,
        width_type='sine'  # 'sine' provides a smoother taper than linear
    )

    # Extrude the path with the defined width transition to create the arm component.
    arm_top = extrude_transition(path=arm_path, transition=width_transition)

    # --- 3. Assemble the full device ---
    # Add the top arm, positioning its start point relative to the component's origin.
    arm_top_ref = c.add_ref(arm_top)
    arm_top_ref.dmovey(y_center_start)

    # Create the bottom arm by mirroring the top arm across the x-axis.
    arm_bottom_ref = c.add_ref(arm_top)
    arm_bottom_ref.dmirror(p1=(0, 0), p2=(1, 0))
    # Position the bottom arm.
    arm_bottom_ref.dmovey(-y_center_start)

    return c

# Instantiate the component.
device = create_device()