import gdsfactory as gf

@gf.cell
def mmi_1x4_vertical():
    """
    Parametric 1x4 MMI component recreation.
    Footprint: 10um (width) x 25um (height).
    Oriented Vertically: Input Bottom, Outputs Top.
    """
    c = gf.Component()

    # --- Geometric Constraints & Parameters ---
    # Total Envelope
    total_width = 10.0
    total_height = 25.0
    
    # Longitudinal Dimensions (Y-axis segments)
    # Tuned to match the visual proportions of the target image
    len_in_wg = 1.5        # Short input stem
    len_in_taper = 2.5     # Input taper region
    len_mmi_body = 6.0     # Main mixing rectangle (shortened to be wider than tall)
    len_out_taper = 5.0    # Output tapered region (lengthened for smoother transition)
    
    # Calculate remaining length for output waveguides to exactly hit 25.0um height
    # 25.0 - (1.5 + 2.5 + 6.0 + 5.0) = 10.0um
    len_out_wg = total_height - (len_in_wg + len_in_taper + len_mmi_body + len_out_taper)

    # Transverse Dimensions (X-axis)
    width_mmi_body = total_width
    width_wg = 1.0         # Waveguide width (approx 1um visually)
    width_taper_max = 2.4  # Max width of tapers at MMI interface (close to pitch for 'V' gap)
    
    # Array Configuration
    n_outputs = 4
    pitch = total_width / n_outputs  # 2.5um pitch

    # Layer definition (Standard waveguide layer)
    layer = (1, 0)

    # --- Construction (Bottom to Top) ---
    
    # 1. Input Waveguide (Bottom Center)
    # Centered at x=0. Bottom edge at y=0.
    wg_in = c << gf.components.rectangle(
        size=(width_wg, len_in_wg), 
        layer=layer, 
        centered=True
    )
    wg_in.movey(len_in_wg / 2) # Move center to correct height

    # 2. Input Taper
    # Tapers from waveguide width (1.0) to max taper width (2.4)
    taper_in = c << gf.components.taper(
        length=len_in_taper, 
        width1=width_wg, 
        width2=width_taper_max, 
        layer=layer
    )
    taper_in.rotate(90) # Rotate to point upwards
    # Move start of taper to end of input waveguide
    taper_in.move((0, len_in_wg))

    # 3. MMI Body
    # Main rectangle centered on the optical axis
    y_body_start = len_in_wg + len_in_taper
    body = c << gf.components.rectangle(
        size=(width_mmi_body, len_mmi_body), 
        layer=layer, 
        centered=True
    )
    # Move to correct vertical position (center of rectangle placed at center of body segment)
    body.move((0, y_body_start + len_mmi_body / 2))

    # 4. Outputs (Array of 4)
    y_output_start = y_body_start + len_mmi_body
    
    # Calculate X positions for 4 outputs centered around 0
    # Indices: -1.5, -0.5, 0.5, 1.5
    indices = [i - (n_outputs - 1) / 2 for i in range(n_outputs)]
    x_positions = [i * pitch for i in indices]

    for x in x_positions:
        # A. Output Taper
        # Tapers from max width (at body) down to waveguide width
        # Note: width1 is start (bottom), width2 is end (top)
        t_out = c << gf.components.taper(
            length=len_out_taper, 
            width1=width_taper_max, 
            width2=width_wg, 
            layer=layer
        )
        t_out.rotate(90)
        t_out.move((x, y_output_start))

        # B. Output Waveguide
        # Straight section extending to the top of the component
        y_wg_start = y_output_start + len_out_taper
        wg_out = c << gf.components.rectangle(
            size=(width_wg, len_out_wg), 
            layer=layer, 
            centered=True
        )
        wg_out.move((x, y_wg_start + len_out_wg / 2))

    return c

# Generate and Save GDS
device = mmi_1x4_vertical()
device.write_gds("mmi_1x4_vertical.gds")
device.show()