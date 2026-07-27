import gdsfactory as gf

@gf.cell
def mmi_1x4_vertical():
    """
    Parametric 1x4 MMI component recreation.
    Footprint: 10um (width) x 25um (height).
    Oriented Vertically: Input Bottom, Outputs Top.
    """
    c = gf.Component()

    # --- Parameters ---
    # We construct it horizontally first (Length=25, Width=10)
    # then rotate it to match the vertical image.
    total_length = 25.0  # Becomes Height
    total_width = 10.0   # Becomes Width
    
    taper_len = 6.0      # Slightly longer tapers to match original silhouette
    mmi_len = total_length - 2 * taper_len  # 25 - 12 = 13.0
    mmi_wid = total_width
    
    wg_width = 0.5
    # Increased taper width at body to 2.25 to reduce gaps between outputs
    mmi_taper_width = 2.25 

    # Create a container for the horizontal construction
    mmi_horiz = gf.Component("mmi_internal")

    # --- 1. MMI Body ---
    mmi_body = mmi_horiz << gf.components.rectangle(
        size=(mmi_len, mmi_wid),
        layer=(1, 0),
        centered=True
    )

    # --- 2. Input Taper (Left side -> Will become Bottom) ---
    # Taper widens from waveguide to MMI body
    taper_in_ref = mmi_horiz << gf.components.taper(
        length=taper_len,
        width1=wg_width,
        width2=mmi_taper_width,
        layer=(1, 0)
    )
    # Connect wide end (right side of taper) to left side of body
    # Taper x-extent is [0, taper_len]. We shift it left.
    taper_in_ref.move((-mmi_len/2 - taper_len, 0))

    # --- 3. Output Tapers (Right side -> Will become Top) ---
    # Taper narrows from MMI body to waveguide
    taper_out_template = gf.components.taper(
        length=taper_len,
        width1=mmi_taper_width,
        width2=wg_width,
        layer=(1, 0)
    )
    
    # Calculate spacing for 4 ports
    n_outputs = 4
    pitch = mmi_wid / n_outputs
    y_offsets = [(i - (n_outputs - 1) / 2) * pitch for i in range(n_outputs)]

    for y in y_offsets:
        t_out = mmi_horiz << taper_out_template
        # Position: Start (wide end) at the right edge of the MMI
        t_out.move((mmi_len / 2, y))

    # --- 4. Final Assembly & Rotation ---
    # Add the horizontal MMI to the main cell and rotate 90 degrees
    # This turns the Left Input -> Bottom Input, and Right Outputs -> Top Outputs
    ref = c << mmi_horiz
    ref.rotate(90)

    return c

# Create and save
device = mmi_1x4_vertical()
device.write_gds("mmi_1x4_vertical.gds")
device.show()