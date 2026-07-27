import gdsfactory as gf

@gf.cell
def mmi_1x4_vertical():
    """
    Parametric 1x4 MMI component recreation.
    Footprint: 10um (width) x 25um (height).
    Oriented Vertically: Input Bottom, Outputs Top.
    """
    c = gf.Component()

    # --- Dimensions Setup ---
    # Construct horizontally (along X), then rotate.
    
    # Target Constraints
    total_width_target = 10.0   # Final Width (X after rotation)
    total_height_target = 25.0  # Final Height (Y after rotation)

    # Component Lengths (Sum to total_height_target = 25.0)
    len_body = 8.0              # Length of the central rectangular mixing region
    len_taper_in = 2.0          # Length of input taper (short triangle)
    len_wg_in = 2.0             # Length of input straight waveguide (stick at bottom)
    len_taper_out = 4.0         # Length of output tapers
    
    # Calculate remaining length for output waveguides
    # 25.0 - (2.0 + 2.0 + 8.0 + 4.0) = 9.0
    len_wg_out = total_height_target - (len_wg_in + len_taper_in + len_body + len_taper_out)

    # Widths
    width_mmi_body = total_width_target
    width_wg = 0.8              # Width of the straight waveguides
    width_taper_max = 2.4       # Max width of taper (fitting within 2.5um pitch)
    
    # Output Array Specs
    n_outputs = 4
    pitch = width_mmi_body / n_outputs 

    # Define Cross Section for straight waveguides
    xs_wg = gf.cross_section.cross_section(width=width_wg, layer=(1, 0))

    # --- Container for Horizontal Construction ---
    mmi_internal = gf.Component("mmi_internal_build")

    # 1. MMI Body (centered at 0,0)
    # Extends from x = -4.0 to x = +4.0
    body = mmi_internal << gf.components.rectangle(
        size=(len_body, width_mmi_body),
        layer=(1, 0),
        centered=True
    )

    # 2. Input Section (Left side -> Becomes Bottom)
    # A. Input Taper (Narrow -> Wide)
    # By default, taper created at (0,0) [narrow] to (length, 0) [wide]
    t_in = mmi_internal << gf.components.taper(
        length=len_taper_in,
        width1=width_wg,
        width2=width_taper_max,
        layer=(1, 0)
    )
    # Move manually to align wide end with left edge of body
    # Target position for wide end: (-len_body/2, 0)
    # Current position of wide end (o2): (len_taper_in, 0)
    # Shift = Target - Current
    shift_x_in = (-len_body/2) - len_taper_in
    t_in.move((shift_x_in, 0))

    # B. Input Straight Waveguide
    w_in = mmi_internal << gf.components.straight(
        length=len_wg_in,
        cross_section=xs_wg
    )
    # Connect end of waveguide (o2) to start of taper (o1)
    w_in.connect("o2", t_in.ports["o1"])

    # 3. Output Section (Right side -> Becomes Top)
    y_offsets = [(i - (n_outputs - 1) / 2) * pitch for i in range(n_outputs)]

    for y in y_offsets:
        # A. Output Taper (Wide -> Narrow)
        # width1=wide, width2=narrow
        t_out = mmi_internal << gf.components.taper(
            length=len_taper_out,
            width1=width_taper_max,
            width2=width_wg,
            layer=(1, 0)
        )
        # Move manually to align wide end (o1) with right edge of body
        # Target position for o1: (len_body/2, y)
        # Current position of o1: (0, 0)
        t_out.move((len_body/2, y))
        
        # B. Output Straight Waveguide
        w_out = mmi_internal << gf.components.straight(
            length=len_wg_out,
            cross_section=xs_wg
        )
        # Connect start of waveguide (o1) to end of taper (o2)
        w_out.connect("o1", t_out.ports["o2"])

    # --- 4. Final Assembly & Rotation ---
    # Add the constructed horizontal component to the main cell
    ref = c << mmi_internal
    
    # Rotate 90 degrees Counter-Clockwise
    # Input (Left) -> Bottom
    # Outputs (Right) -> Top
    ref.rotate(90)

    return c

# Create and save
device = mmi_1x4_vertical()
device.write_gds("mmi_1x4_vertical.gds")
device.show()