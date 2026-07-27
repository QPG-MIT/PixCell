import gdsfactory as gf

@gf.cell
def create_arm(
    interaction_length: float = 15.5,
    wg_width: float = 0.14,
    bend_radius: float = 0.2,
    taper_length: float = 2.0,
    swoop_radius: float = 0.2,
    swoop_angle: float = -30.0,
):
    """
    Creates one of the U-shaped arms by connecting a sequence of
    parametric primitive components.
    """
    c = gf.Component()
    
    xs = gf.cross_section.cross_section(width=wg_width, radius=swoop_radius)

    # 1. Define the primitive components for the arm's path
    swoop_in = gf.components.bend_euler(
        radius=swoop_radius, angle=swoop_angle, cross_section=xs
    )
    interact_straight = gf.components.straight(
        length=interaction_length, cross_section=xs
    )
    u_bend = gf.components.bend_euler(radius=bend_radius, angle=180, cross_section=xs)
    
    return_straight = gf.components.straight(
        length=interaction_length, cross_section=xs
    )
    taper_out = gf.components.taper(
        length=taper_length, width1=wg_width, width2=0.01, cross_section=xs
    )

    # 2. Add component references to the cell
    r_swoop = c << swoop_in
    r_interact = c << interact_straight
    r_ubend = c << u_bend
    r_return = c << return_straight
    r_taper = c << taper_out

    # 3. Connect the primitives in sequence to form the continuous arm
    r_interact.connect("o1", r_swoop.ports["o2"])
    r_ubend.connect("o1", r_interact.ports["o2"])
    r_return.connect("o1", r_ubend.ports["o2"])
    r_taper.connect("o1", r_return.ports["o2"])

    # FIX: The "off-grid instances" error is caused by floating-point inaccuracies
    # from the chain of 'connect' operations. flatten() merges all the geometry
    # into the current cell and snaps vertices to the grid, resolving the issue.
    c.flatten()
    
    return c


@gf.cell
def reconstructed_device():
    """
    Recreates the full device from the image by assembling the central waveguide,
    the two symmetric arms, and the two gratings.
    """
    # 1. Define parameters derived from the footprint [18.24, 0.7] and visual cues
    wg_width = 0.14
    gap = 0.14
    
    interaction_length = 15.6
    u_bend_radius = 0.2
    taper_len = 2.0
    swoop_rad = 0.15
    swoop_ang = -25.0

    # 2. Create the arm sub-component (which is now flattened and grid-aligned)
    arm = create_arm(
        interaction_length=interaction_length,
        wg_width=wg_width,
        bend_radius=u_bend_radius,
        taper_length=taper_len,
        swoop_radius=swoop_rad,
        swoop_angle=swoop_ang,
    )

    # 3. Create the grating component
    grating_period = 0.35
    grating_duty_cycle = 0.4
    grating_rect_width = grating_period * grating_duty_cycle
    num_periods = int(interaction_length / grating_period)
    
    grating_unit = gf.components.rectangle(size=(grating_rect_width, gap))
    grating_array = gf.Component("grating_array")
    grating_array.add_array(
        component=grating_unit,
        columns=num_periods,
        rows=1,
        spacing=(grating_period, 0),
    )

    # 4. Create the central straight waveguide
    center_wg = gf.components.straight(length=arm.xsize, width=wg_width)
    
    # 5. Assemble the final device
    c = gf.Component("FinalDevice")
    
    arm_top_ref = c << arm
    arm_bottom_ref = c << arm
    
    y_offset_arm = wg_width / 2 + gap
    arm_top_ref.y = y_offset_arm
    arm_bottom_ref.mirror()
    arm_bottom_ref.y = -y_offset_arm

    swoop_ref_dims = gf.components.bend_euler(radius=swoop_rad, angle=swoop_ang).size_info
    grating_start_x = swoop_ref_dims.width

    grating_top_ref = c << grating_array
    grating_bottom_ref = c << grating_array
    
    y_offset_grating = wg_width / 2 + gap / 2
    grating_top_ref.x = grating_start_x
    grating_top_ref.y = y_offset_grating
    grating_bottom_ref.x = grating_start_x
    grating_bottom_ref.y = -y_offset_grating
    
    c << center_wg
    
    c.move_origin(-c.center)
    
    # It's also good practice to flatten the final top-level component
    # to ensure the entire layout is grid-compliant before exporting.
    c.flatten()

    return c

# Generate the GDS cell
device = reconstructed_device()
# To display the component in a GDS viewer:
# device.show() 
# To save to a GDS file:
# device.write_gds("reconstructed_device.gds")