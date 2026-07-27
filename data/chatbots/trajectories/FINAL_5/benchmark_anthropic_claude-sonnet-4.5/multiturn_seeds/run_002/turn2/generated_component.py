import gdsfactory as gf

@gf.cell
def dual_taper_grating_coupler():
    """
    Recreates the dual waveguide structure with tapered ends and grating sections.
    Top waveguide: sharp triangular taper (left) → grating → solid section (right)
    Bottom waveguide: solid (left) → grating → solid (right)
    """
    c = gf.Component()
    
    # Device dimensions from footprint
    total_length = 18.24
    total_height = 0.7
    
    # Structure parameters
    gap = 0.06  # Gap between top and bottom waveguides
    wg_height = (total_height - gap) / 2  # Height of each waveguide ~0.32 µm
    
    # Section lengths (adjusted based on visual proportions)
    taper_length = 3.0  # Sharp triangular taper on top
    grating_length = 8.5  # Long grating section
    post_grating_length = 6.74  # Right solid section
    
    # Grating parameters
    period = 0.12  # Tighter spacing to match image
    duty_cycle = 0.5  # 50% duty cycle
    
    # === TOP WAVEGUIDE ===
    x = 0
    
    # Left sharp taper (triangular point)
    taper_top_left = c << gf.components.taper(
        length=taper_length, 
        width1=0.01,  # Very sharp point
        width2=wg_height,
        layer=(1, 0)
    )
    taper_top_left.xmin = x
    taper_top_left.ymin = gap/2
    x += taper_length
    
    # Grating section (vertical bars)
    num_periods = int(grating_length / period)
    for i in range(num_periods):
        bar_x = x + i * period
        bar_width = period * duty_cycle
        bar = c << gf.components.rectangle(
            size=(bar_width, wg_height),
            layer=(1, 0)
        )
        bar.xmin = bar_x
        bar.ymin = gap/2
    x += grating_length
    
    # Post-grating solid section (right)
    post_grating_top = c << gf.components.rectangle(
        size=(post_grating_length, wg_height),
        layer=(1, 0)
    )
    post_grating_top.xmin = x
    post_grating_top.ymin = gap/2
    
    # === BOTTOM WAVEGUIDE (NO TAPER - rectangular throughout) ===
    x = 0
    
    # Left solid section
    pre_grating_bottom = c << gf.components.rectangle(
        size=(taper_length, wg_height),
        layer=(1, 0)
    )
    pre_grating_bottom.xmin = x
    pre_grating_bottom.ymax = -gap/2
    x += taper_length
    
    # Grating section (vertical bars)
    for i in range(num_periods):
        bar_x = x + i * period
        bar_width = period * duty_cycle
        bar = c << gf.components.rectangle(
            size=(bar_width, wg_height),
            layer=(1, 0)
        )
        bar.xmin = bar_x
        bar.ymax = -gap/2
    x += grating_length
    
    # Post-grating solid section (right)
    post_grating_bottom = c << gf.components.rectangle(
        size=(post_grating_length, wg_height),
        layer=(1, 0)
    )
    post_grating_bottom.xmin = x
    post_grating_bottom.ymax = -gap/2
    
    # === CENTER SEPARATOR LINE ===
    # Spans from end of taper to end of device
    center_line_length = grating_length + post_grating_length
    center_line = c << gf.components.rectangle(
        size=(center_line_length, 0.02),
        layer=(1, 0)
    )
    center_line.xmin = taper_length
    center_line.ycenter = 0
    
    return c


# Generate the device
device = dual_taper_grating_coupler()

# Save to GDS
device.write_gds("dual_taper_grating_coupler.gds")

print(f"Device generated successfully!")
print(f"Device bounding box: {device.bbox}")