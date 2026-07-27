import gdsfactory as gf

@gf.cell
def bragg_waveguide(
    length=40.0,
    period=0.6,
    width=0.5,
    corrugation_width=0.3,
    layer=(1, 0)
):
    """
    Creates a straight waveguide with periodic rectangular corrugations (gratings).
    """
    c = gf.Component()
    
    # Define cross section for the main waveguide body
    xs = gf.cross_section.cross_section(width=width, layer=layer)
    
    # Add the central straight waveguide core
    wg = c << gf.components.straight(length=length, cross_section=xs)
    
    # Add periodic grating teeth
    # We calculate the number of periods that fit
    n_periods = int(length / period)
    tooth_width = period / 2
    total_tooth_height = width + corrugation_width
    
    for i in range(n_periods):
        x_pos = i * period
        # Create a rectangular tooth
        tooth = c << gf.components.rectangle(
            size=(tooth_width, total_tooth_height),
            layer=layer,
            centered=True
        )
        # Position the tooth along the waveguide
        # Shift x by half period to align properly, y is centered on 0
        tooth.move((x_pos + period/2, 0))
        
    # Expose the ports from the underlying waveguide
    c.add_port("o1", port=wg.ports["o1"])
    c.add_port("o2", port=wg.ports["o2"])
    
    # Flatten the component to merge polygons and snap to grid.
    # This prevents off-grid issues when this component is referenced and rotated.
    c.flatten()
    return c

@gf.cell
def loop_arm(
    grating_len=40.0,
    bend_radius=5.0,
    width=0.5,
    layer=(1, 0)
):
    """
    Creates one half of the loop structure:
    Input Tail (Curved) -> Grating -> 180 Bend -> Return Straight
    """
    c = gf.Component()
    
    # Define cross-section. Explicit radius is required to allow tighter bends 
    # than the default (which is often 10um).
    xs = gf.cross_section.cross_section(width=width, layer=layer, radius=bend_radius)
    
    # 1. Grating Section
    grating = c << bragg_waveguide(length=grating_len, width=width, layer=layer)
    
    # 2. 180 Degree U-Turn
    # We use bend_euler for the main 180 turn for a smooth adiabatic transition
    u_bend = c << gf.components.bend_euler(
        radius=bend_radius, 
        angle=180, 
        cross_section=xs
    )
    # Connect the start of the bend to the end (right side) of the grating
    u_bend.connect("o1", grating.ports["o2"])
    
    # 3. Return Straight Path
    # This runs parallel to the grating
    return_wg = c << gf.components.straight(
        length=grating_len + 15, # Slightly longer to extend past the input
        cross_section=xs
    )
    return_wg.connect("o1", u_bend.ports["o2"])
    
    # 4. Input Tail (Curved entry)
    # We use bend_circular for the 45-degree angle to avoid Euler parameter warnings
    # and potential geometry generation issues at odd angles.
    input_tail = c << gf.components.bend_circular(
        radius=15, 
        angle=45, 
        cross_section=xs
    )
    # Connect the tail so it curves OUTWARDS from the grating input.
    # Connecting tail.o2 to grating.o1 achieves the flare-out effect.
    input_tail.connect("o2", grating.ports["o1"])
    
    # Flatten the cell. This is critical because the 45-degree rotation creates 
    # vertices at irrational coordinates. Flattening snaps them to the manufacturing grid
    # and resolves "Found off-grid instances" errors.
    c.flatten()
    return c

@gf.cell
def contra_directional_coupler_device():
    """
    Assembles the full device: Top Arm, Bottom Arm (mirrored), and Central Bus.
    """
    c = gf.Component()
    
    # Design Parameters derived from image analysis
    wg_width = 1.2      # Relatively wide waveguides
    layer = (1, 0)
    gap = 0.4           # Gap between the grating teeth and central bus area
    bend_radius = 5.0   # Tight loop radius
    
    # ---------------------------------------------------------
    # TOP ARM CONSTRUCTION
    # ---------------------------------------------------------
    top_arm = c << loop_arm(
        width=wg_width, 
        layer=layer, 
        bend_radius=bend_radius
    )
    
    # Calculate Y offset for the Top Arm
    # The grating inside loop_arm is centered at y=0.
    # We want the gap between the two arms to be `gap`.
    # Distance from centerline (y=0) to grating center = gap/2 + width/2
    y_offset = gap/2 + wg_width/2
    top_arm.movey(y_offset)
    
    # ---------------------------------------------------------
    # BOTTOM ARM CONSTRUCTION
    # ---------------------------------------------------------
    # The bottom arm is a mirror image of the top arm.
    bot_arm = c << loop_arm(
        width=wg_width, 
        layer=layer, 
        bend_radius=bend_radius
    )
    
    # Mirror across the X-axis (line from 0,0 to 1,0)
    bot_arm.mirror(p1=(0,0), p2=(1,0))
    
    # Move to the negative Y position
    bot_arm.movey(-y_offset)
    
    # ---------------------------------------------------------
    # CENTRAL BUS WAVEGUIDE
    # ---------------------------------------------------------
    # Thin waveguide running through the center
    thin_xs = gf.cross_section.cross_section(width=0.15, layer=layer)
    center_line = c << gf.components.straight(length=90, cross_section=thin_xs)
    
    # Align the center line horizontally with the arms.
    # The arms start at X=0 (grating start) roughly. The grating is 40um long.
    # Center of grating is at X=20. We center the 90um line at X=20.
    center_line.x = 20
    center_line.y = 0

    return c

if __name__ == "__main__":
    # Generate the GDS file
    device = contra_directional_coupler_device()
    device.show() # Opens in KLayout if configured
    device.write_gds("contra_dc_device.gds")
    print("GDS file written: contra_dc_device.gds")