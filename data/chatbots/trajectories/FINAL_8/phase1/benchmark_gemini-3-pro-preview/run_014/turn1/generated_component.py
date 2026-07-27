import gdsfactory as gf

@gf.cell
def striped_coupler_device():
    """
    Recreates the striped directional coupler device within a 120um x 4um footprint.
    """
    c = gf.Component()

    # 1. Define the "Striped" Cross Section
    # The image shows each bus consists of 3 parallel lines.
    # We create a custom cross_section with a center core and two offset sections.
    # Dimensions are tuned to look like the image (thin lines, tight spacing).
    
    width_line = 0.15
    gap_internal = 0.15
    offset_val = width_line + gap_internal # 0.3
    
    # Define sections for the outer stripes
    s_top = gf.Section(width=width_line, offset=offset_val, layer=(1, 0))
    s_bot = gf.Section(width=width_line, offset=-offset_val, layer=(1, 0))

    # Create the cross section (center width handles the middle stripe)
    xs_bundle = gf.cross_section.cross_section(
        width=width_line,
        sections=[s_top, s_bot],
        layer=(1, 0)
    )

    # 2. Define Parametric Dimensions to fit 120x4 footprint
    total_length = 120.0
    bend_length = 30.0
    coupling_length = total_length - 2 * bend_length  # 60.0
    
    # Vertical positions (y) relative to center (0,0)
    # The device fits in 4um, so max y is 2.0, min y is -2.0.
    y_input_top = 1.5
    y_input_bot = -1.5
    
    # The coupling region is tighter in the center
    y_couple_top = 0.6
    y_couple_bot = -0.6
    
    # Calculate the vertical shift (dy) for the S-bends
    dy_top = y_couple_top - y_input_top   # Negative (going down)
    dy_bot = y_couple_bot - y_input_bot   # Positive (going up)

    # 3. Generate Primitives
    
    # Straight coupling segment
    wg_straight = gf.components.straight(
        length=coupling_length, 
        cross_section=xs_bundle
    )

    # Top S-bends (Input: high->low, Output: low->high)
    bend_s_down = gf.components.bend_s(
        size=(bend_length, dy_top), 
        cross_section=xs_bundle
    )
    bend_s_up = gf.components.bend_s(
        size=(bend_length, -dy_top), # Invert dy to go back up
        cross_section=xs_bundle
    )

    # Bottom S-bends (Input: low->high, Output: high->low)
    bend_s_rise = gf.components.bend_s(
        size=(bend_length, dy_bot), 
        cross_section=xs_bundle
    )
    bend_s_fall = gf.components.bend_s(
        size=(bend_length, -dy_bot), 
        cross_section=xs_bundle
    )

    # 4. Assembly - Connect components sequentially
    
    # --- Top Arm Construction ---
    # 1. Input Bend
    t1 = c << bend_s_down
    t1.movey(y_input_top) # Move start point to input height
    
    # 2. Straight Section
    t2 = c << wg_straight
    t2.connect("o1", t1.ports["o2"])
    
    # 3. Output Bend
    t3 = c << bend_s_up
    t3.connect("o1", t2.ports["o2"])

    # --- Bottom Arm Construction ---
    # 1. Input Bend
    b1 = c << bend_s_rise
    b1.movey(y_input_bot)
    
    # 2. Straight Section
    b2 = c << wg_straight
    b2.connect("o1", b1.ports["o2"])
    
    # 3. Output Bend
    b3 = c << bend_s_fall
    b3.connect("o1", b2.ports["o2"])

    # 5. Expose Ports
    c.add_port("o1", port=t1.ports["o1"])
    c.add_port("o2", port=b1.ports["o1"])
    c.add_port("o3", port=t3.ports["o2"])
    c.add_port("o4", port=b3.ports["o2"])

    return c

# Create and save the device
device = striped_coupler_device()
device.show() # Shows in KLayout if installed
device.write_gds("striped_coupler.gds")