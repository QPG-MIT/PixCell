import gdsfactory as gf

@gf.cell
def recreated_device():
    """
    Recreates the optical splitter from the provided image using GDSFactory.

    The device is constructed by composing three parametric components:
    1. A central linear taper (`gf.components.taper`).
    2. A top arm created by extruding a smooth path with a variable width
       (`gf.path.smooth`, `gf.path.transition`, `gf.path.extrude_transition`).
    3. A bottom arm created by mirroring the top arm.

    All dimensions are calculated to match the specified device footprint of [40.0, 1.7] um.
    """
    c = gf.Component()

    # --- 1. Define Device Parameters from Footprint ---
    total_length = 40.0
    total_height = 1.7

    # Parameters for the two output waveguides
    output_wg_width = 0.5
    # Calculate the final y-position of the top arm's center to match the total height
    # y_center = (total_height / 2) - (wg_width / 2)
    output_arm_y_center = (total_height / 2) - (output_wg_width / 2)  # 0.85 - 0.25 = 0.6

    # Parameters for the central tapering element
    mid_taper_length = 25.0
    mid_taper_width_start = 0.4
    mid_taper_width_end = 0.02  # Taper to a sharp point

    # Parameters for the input side of the outer arms
    input_arm_width = 0.2
    input_gap = 0.1
    # Calculate the initial y-position of the top arm's center
    # y_center = (center_taper_width/2) + gap + (arm_width/2)
    input_arm_y_center = (mid_taper_width_start / 2) + input_gap + (input_arm_width / 2)

    # --- 2. Create the Central Taper ---
    t_mid = gf.components.taper(
        length=mid_taper_length,
        width1=mid_taper_width_start,
        width2=mid_taper_width_end,
    )

    # --- 3. Create the Top Arm via Path Extrusion ---
    # Define the centerline path: straight for 15um, then a smooth curve
    path_points = [
        (0, input_arm_y_center),
        (15, input_arm_y_center),
        (total_length, output_arm_y_center),
    ]
    # gf.path.smooth creates a path with automatically generated bends
    top_arm_path = gf.path.smooth(points=path_points, radius=30)

    # Define the width transition along the path
    xs_start = gf.cross_section.cross_section(width=input_arm_width)
    xs_end = gf.cross_section.cross_section(width=output_wg_width)
    width_transition = gf.path.transition(
        cross_section1=xs_start, cross_section2=xs_end, width_type="sine"
    )

    # Extrude the path with the width transition to create the solid component
    # FIX: Use gf.path.extrude_transition for varying widths.
    arm_top = gf.path.extrude_transition(top_arm_path, transition=width_transition)

    # --- 4. Assemble the Final Device ---
    # Add the central taper, aligning its start to x=0
    ref_mid = c << t_mid
    ref_mid.xmin = 0

    # Add the top arm
    ref_top = c << arm_top
    ref_top.xmin = 0

    # Add the bottom arm by creating a mirrored reference to the top arm
    ref_bot = c << arm_top
    ref_bot.mirror(p1=(0, 0), p2=(1, 0))  # Mirror across the x-axis
    ref_bot.xmin = 0
    
    # Add ports for connectivity
    c.add_port("o1", port=ref_mid.ports["o1"])
    c.add_port("o2", port=ref_top.ports["o2"])
    c.add_port("o3", port=ref_bot.ports["o2"])

    return c

# Create an instance of the device
device = recreated_device()
# To verify, you can uncomment the following line:
# device.show()