import gdsfactory as gf

@gf.cell
def create_arm(
    length: float,
    taper_length: float,
    waveguide_width: float,
    grating_teeth: int = 0,
    grating_period: float = 0.2,
    grating_tooth_width: float = 0.1,
    grating_tooth_height: float = 0.1,
) -> gf.Component:
    """
    Creates one arm of the U-shaped structure. It consists of a straight
    waveguide, a taper, and an optional corrugated grating on one side.

    The component has two ports, 'o1' at the straight end and 'o2' at the taper tip.
    """
    c = gf.Component()
    
    straight_length = length - taper_length
    
    # Add the main straight waveguide section
    s = c << gf.components.straight(length=straight_length, width=waveguide_width)
    
    # Add the taper at the end
    t = c << gf.components.taper(
        length=taper_length, width1=waveguide_width, width2=0.01, with_two_ports=True
    )
    t.connect("o1", s.ports["o2"])

    # Add grating teeth if specified
    if grating_teeth > 0:
        tooth = gf.components.rectangle(
            size=(grating_tooth_width, grating_tooth_height), centered=True
        )
        # Position teeth along the "bottom" edge of the straight section (at y < 0)
        y_position = -waveguide_width / 2 - grating_tooth_height / 2
        
        # Center the grating along the straight section
        grating_span = (grating_teeth - 1) * grating_period
        x_start = (straight_length - grating_span) / 2
        
        for i in range(grating_teeth):
            tooth_ref = c.add_ref(tooth)
            tooth_ref.move((x_start + i * grating_period, y_position))
            
    c.add_port("o1", port=s.ports["o1"])
    c.add_port("o2", port=t.ports["o2"])
    return c


@gf.cell
def symmetric_grating_coupler() -> gf.Component:
    """
    Creates the full device by assembling and mirroring the U-shaped arms.
    The parameters are derived to match the provided footprint and snapped to the grid.
    """
    # 1. Define parameters based on footprint and a robust geometric model
    footprint_w, footprint_h = 18.24, 0.7
    grid_size = 0.002  # Grid must be a multiple of 2 dbu (2 * 1nm)
    central_line_width = 0.02

    # **FIX**: Use a more robust geometric derivation for waveguide width to avoid
    # floating point values that round to an odd dbu number (like 39).
    # Model: H = w_central + 2*gap + 2*tooth_h + 4*radius + w_wg
    # With proportional assumptions (r=3w, th=2w, g=w):
    # 0.7 ≈ 0.02 + 2w + 4w + 12w + w = 0.02 + 19w => w ≈ 0.68 / 19
    ideal_w_wg = (footprint_h - central_line_width) / 19.0  # ≈ 0.03578...
    
    # Snap the robustly-calculated width to the valid 2nm grid
    w_wg = gf.snap.snap_to_grid(ideal_w_wg, grid_size) # Results in 0.036 um (36 dbu)

    # Recalculate related dimensions based on the new snapped width
    radius = 3 * w_wg
    tooth_height = gf.snap.snap_to_grid(2 * w_wg, grid_size) # 0.072 um (72 dbu)
    
    arm_length = footprint_w - radius
    taper_length = 2.0

    # Grating parameters
    n_teeth = 100
    grating_length = 15.0
    grating_period = grating_length / n_teeth
    ideal_grating_tooth_width = grating_period * 0.5  # 0.075 (75 dbu - odd)

    # Snap the grating tooth width to the valid 2nm grid
    grating_tooth_width = gf.snap.snap_to_grid(ideal_grating_tooth_width, grid_size) # 0.076 um (76 dbu)

    # 2. Create a single U-shaped component
    u_arm_component = gf.Component("U_Grating_Arm")

    bend = u_arm_component << gf.components.bend_euler(
        radius=radius, angle=180, width=w_wg
    )
    bend.movex(arm_length)

    arm_plain = create_arm(
        length=arm_length,
        taper_length=taper_length,
        waveguide_width=w_wg,
    )
    arm_plain_ref = u_arm_component << arm_plain
    arm_plain_ref.connect("o1", bend.ports["o1"])

    arm_grating = create_arm(
        length=arm_length,
        taper_length=taper_length,
        waveguide_width=w_wg,
        grating_teeth=n_teeth,
        grating_period=grating_period,
        grating_tooth_width=grating_tooth_width,
        grating_tooth_height=tooth_height,
    )
    arm_grating_ref = u_arm_component << arm_grating
    arm_grating_ref.connect("o1", bend.ports["o2"])

    # 3. Assemble the final device
    device = gf.Component("Symmetric_Grating_Structure")

    center_x = footprint_w / 2
    central_line = device << gf.components.rectangle(
        size=(footprint_w, central_line_width), centered=True, center=(center_x, 0)
    )

    # Calculate vertical placement for symmetry
    gap = w_wg # Assume gap is same as waveguide width
    y_center = (central_line_width / 2) + gap + tooth_height + radius

    top_ref = device << u_arm_component
    top_ref.movey(y_center)

    bottom_ref = device << u_arm_component
    bottom_ref.mirror(p1=(0, 0), p2=(1, 0))
    bottom_ref.movey(-y_center)

    return device

# Instantiate the final component
final_device = symmetric_grating_coupler()