import gdsfactory as gf

@gf.cell
def directional_coupler_120_4():
    """
    Directional coupler with a 120um x 4um footprint.
    Constructed using straight waveguides for the coupling region and s-bends for I/O.
    """
    c = gf.Component()

    # --- Parameters derived from Footprint Constraint [120, 4] ---
    # Total dimensions
    total_length = 120.0
    total_height = 4.0
    
    # Waveguide geometry
    wg_width = 0.5
    coupling_gap = 0.2
    
    # Longitudinal decomposition
    # Based on visual inspection, the straight coupling region is roughly half the total length.
    length_straight = 60.0
    # The remaining length is split between the two bend sections.
    length_bend = (total_length - length_straight) / 2  # Result: 30.0 um
    
    # Vertical decomposition
    # Calculate the y-offset for the input/output ports (outermost positions)
    # y = +/- (Height/2 - Width/2)
    y_io_center = (total_height / 2) - (wg_width / 2)
    
    # Calculate the y-offset for the coupling region (innermost positions)
    # y = +/- (Gap/2 + Width/2)
    y_couple_center = (coupling_gap / 2) + (wg_width / 2)
    
    # Calculate the vertical shift (dy) required for the S-bends
    dy_bend = y_io_center - y_couple_center

    # Cross-section definition
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 1. Central Coupling Region ---
    # We construct the coupling region manually with two straights to ensure precise placement.
    # Top coupling arm
    wg_top = c << gf.components.straight(length=length_straight, cross_section=xs)
    wg_top.movey(y_couple_center)
    
    # Bottom coupling arm
    wg_bot = c << gf.components.straight(length=length_straight, cross_section=xs)
    wg_bot.movey(-y_couple_center)

    # --- 2. Input S-Bends (Left Side) ---
    # Top Input: Connects to the left side of the top straight.
    # The bend needs to span from the high input Y to the lower coupling Y.
    # Since we connect to the 'straight' (right side of connection), the bend's end 'o2' connects to straight 'o1'.
    # A negative dy in the bend primitive means 'o2' is lower than 'o1'.
    bend_in_top = c << gf.components.bend_s(size=(length_bend, -dy_bend), cross_section=xs)
    bend_in_top.connect("o2", wg_top.ports["o1"])
    
    # Bottom Input: Connects to the left side of the bottom straight.
    # The bend needs to span from the low input Y to the higher coupling Y.
    # A positive dy means 'o2' is higher than 'o1'.
    bend_in_bot = c << gf.components.bend_s(size=(length_bend, dy_bend), cross_section=xs)
    bend_in_bot.connect("o2", wg_bot.ports["o1"])

    # --- 3. Output S-Bends (Right Side) ---
    # Top Output: Connects to the right side of the top straight.
    # The bend goes from low coupling Y to high output Y.
    # We connect the start 'o1' of the bend to the end 'o2' of the straight.
    bend_out_top = c << gf.components.bend_s(size=(length_bend, dy_bend), cross_section=xs)
    bend_out_top.connect("o1", wg_top.ports["o2"])
    
    # Bottom Output: Connects to the right side of the bottom straight.
    # The bend goes from high coupling Y to low output Y.
    bend_out_bot = c << gf.components.bend_s(size=(length_bend, -dy_bend), cross_section=xs)
    bend_out_bot.connect("o1", wg_bot.ports["o2"])

    # --- 4. Expose Ports ---
    c.add_port("o1", port=bend_in_bot.ports["o1"]) # Bottom Left
    c.add_port("o2", port=bend_in_top.ports["o1"]) # Top Left
    c.add_port("o3", port=bend_out_top.ports["o2"]) # Top Right
    c.add_port("o4", port=bend_out_bot.ports["o2"]) # Bottom Right

    return c

# Generate and save the device
device = directional_coupler_120_4()
device.write_gds("directional_coupler.gds")