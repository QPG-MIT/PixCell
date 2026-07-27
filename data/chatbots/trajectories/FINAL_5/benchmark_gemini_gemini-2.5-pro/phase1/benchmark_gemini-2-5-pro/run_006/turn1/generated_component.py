import gdsfactory as gf

@gf.cell
def create_photonic_device():
    """
    Creates the symmetrical photonic device shown in the image by composing
    parametric GDSFactory primitives.
    """
    # --- Parameters ---
    # Derived from footprint [18.24, 0.7] and visual proportions.
    wg_width = 0.232
    gap = 0.078
    bar_width = 0.078

    # Geometric parameters to match the total width of 18.24 um
    bend_radius = 1.0
    taper_len_start = 5.3
    straight_len = 10.6
    grating_section_len = 10.1  # Length of the straight section for grating placement

    # Parameters for the curved, tapering end
    end_angle = -60
    end_radius_factor = 1.5

    # Parameters for the grating teeth
    grating_period = 0.4
    grating_ff = 0.5  # Fill factor of the grating teeth

    # --- FIX: Define a custom cross_section to allow for tight bends ---
    # The default min_bend_radius is 5.0, but this design needs a smaller one.
    xs = gf.cross_section.cross_section(width=wg_width, radius_min=0.5)

    # --- 1. Build a single solid arm component ---
    arm = gf.Component("arm_component")

    # Define the primitive components for the arm, using the custom cross_section
    taper_start = gf.components.taper(
        length=taper_len_start, width1=0.02, width2=wg_width
    )
    wg_top_straight = gf.components.straight(length=straight_len, cross_section=xs)
    bend_180 = gf.components.bend_euler(radius=bend_radius, angle=180, p=0.5, cross_section=xs)
    wg_bottom_straight = gf.components.straight(
        length=grating_section_len, cross_section=xs
    )

    # The end curve is a path with a width transition (taper)
    path_end = gf.path.euler(radius=bend_radius * end_radius_factor, angle=end_angle)

    # Define the cross-sections for the transition, also with a small radius_min
    xs_tip = gf.cross_section.cross_section(width=0.02, radius_min=0.5)
    width_transition = gf.path.transition(cross_section1=xs, cross_section2=xs_tip)
    curved_taper_end = gf.path.extrude_transition(path_end, transition=width_transition)

    # Assemble the arm by adding and connecting the component references
    r_taper = arm << taper_start
    r_wg_top = arm << wg_top_straight
    r_bend = arm << bend_180
    r_wg_bottom = arm << wg_bottom_straight
    r_curved_taper = arm << curved_taper_end

    r_wg_top.connect("o1", r_taper.ports["o2"])
    r_bend.connect("o1", r_wg_top.ports["o2"])
    r_wg_bottom.connect("o1", r_bend.ports["o2"])
    r_curved_taper.connect("o1", r_wg_bottom.ports["o2"])

    # --- 2. Build the final device with all parts ---
    c = gf.Component("final_device")

    # Add and place the top and bottom arms
    top_arm_ref = c << arm
    bottom_arm_ref = c << arm
    bottom_arm_ref.mirror(p1=(0, 0), p2=(1, 0))  # Mirror across x-axis

    # The y-position of the inner straight waveguide within the arm component
    y_center_in_arm = r_wg_bottom.y

    # Calculate the target y-position for the inner waveguides relative to the origin
    y_target = bar_width / 2 + gap + wg_width / 2

    # Move the arms to their final positions
    top_arm_ref.y = y_target - y_center_in_arm
    bottom_arm_ref.y = -y_target + y_center_in_arm

    # Add the central bar, matching the length of the arms
    bar_length = arm.xsize
    central_bar = c << gf.components.rectangle(size=(bar_length, bar_width))
    central_bar.center = (arm.center[0], 0)

    # --- 3. Add the grating teeth arrays ---
    grating_tooth_width = grating_period * grating_ff
    grating_tooth_height = gap
    num_teeth = int(grating_section_len / grating_period)

    grating_tooth = gf.components.rectangle(
        size=(grating_tooth_width, grating_tooth_height)
    )

    # Create and position the top grating array
    top_grating_ref = c.add_array(
        component=grating_tooth, columns=num_teeth, rows=1, spacing=(grating_period, 0)
    )
    # Align the start of the grating with the start of the inner straight section
    top_grating_ref.xmin = top_arm_ref.x + r_wg_bottom.xmin
    top_grating_ref.y = bar_width / 2  # Place it on top of the central bar

    # Create and position the bottom grating array
    bottom_grating_ref = c.add_array(
        component=grating_tooth, columns=num_teeth, rows=1, spacing=(grating_period, 0)
    )
    bottom_grating_ref.xmin = top_grating_ref.xmin # Align x with top grating
    bottom_grating_ref.ymax = -bar_width / 2 # Place it below the central bar

    return c

# Create an instance of the component to display or save
final_device = create_photonic_device()
# final_device.show() # Uncomment to show the layout in a viewer if installed
# final_device.write_gds("device.gds") # Uncomment to save the layout to a GDS file