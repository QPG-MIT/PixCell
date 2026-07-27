import gdsfactory as gf

@gf.cell
def device_recreation():
    """
    Recreates the trident spot-size converter/coupler from the reference image.
    Dimensions are derived from the [40.0, 1.7] um footprint constraint.
    """
    c = gf.Component()
    
    # --- Parameters ---
    # Global dimensions
    wg_width = 0.4
    layer = (1, 0)
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)
    
    # Longitudinal dimensions (Total = 40um)
    len_input = 20.0     # Length of the middle taper and parallel straight sections
    len_bend = 15.0      # Length of the S-bend transition
    len_output = 5.0     # Length of the final straight output
    
    # Transverse dimensions (Total Height = 1.7um)
    input_gap = 0.25
    # Calculate pitch (center-to-center distance) for input
    # Pitch = width/2 + gap + width/2
    pitch_in = wg_width + input_gap # 0.4/2 + 0.25 + 0.4/2 = 0.65
    
    # Output configuration (Tighter coupling)
    output_gap = 0.2
    pitch_out = wg_width + output_gap # 0.4/2 + 0.2 + 0.4/2 = 0.6 (approx)
    
    # Calculate the vertical shift needed for the S-bends
    # Top arm goes from +0.65 to +0.3 (approx) -> shift is negative
    # Bottom arm goes from -0.65 to -0.3 (approx) -> shift is positive
    y_shift = (pitch_in - (wg_width + output_gap)/2) - (wg_width/2 + output_gap/2)
    # Re-calculating shift strictly:
    y_top_in = pitch_in / 2 + 0.325 # Wait, pitch_in is 0.65. So y_top = 0.65.
    y_top_out = (wg_width + output_gap) / 2 # (0.4 + 0.2)/2 = 0.3
    dy = y_top_out - 0.65 # 0.3 - 0.65 = -0.35
    
    # --- 1. Middle Arm (Taper) ---
    # The middle waveguide tapers from wg_width to a fine tip and terminates.
    taper = c << gf.components.taper(
        length=len_input,
        width1=wg_width,
        width2=0.05, # Tapers to a fine point (below fabrication resolution usually)
        layer=layer
    )
    # Taper defaults to center at (0,0), input at x=0
    
    # --- 2. Top Arm ---
    # Part A: Straight input parallel to taper
    top_straight = c << gf.components.straight(
        length=len_input,
        cross_section=xs
    )
    top_straight.move((0, 0.65)) # Move to y position
    
    # Part B: S-Bend compressing inwards
    top_bend = c << gf.components.bend_s(
        size=(len_bend, dy), # (length, vertical_displacement)
        cross_section=xs
    )
    top_bend.connect("o1", top_straight.ports["o2"])
    
    # Part C: Straight output
    top_out = c << gf.components.straight(
        length=len_output,
        cross_section=xs
    )
    top_out.connect("o1", top_bend.ports["o2"])
    
    # --- 3. Bottom Arm ---
    # Part A: Straight input parallel to taper
    bot_straight = c << gf.components.straight(
        length=len_input,
        cross_section=xs
    )
    bot_straight.move((0, -0.65)) # Mirror of top
    
    # Part B: S-Bend compressing inwards (positive shift to go up)
    bot_bend = c << gf.components.bend_s(
        size=(len_bend, -dy), 
        cross_section=xs
    )
    bot_bend.connect("o1", bot_straight.ports["o2"])
    
    # Part C: Straight output
    bot_out = c << gf.components.straight(
        length=len_output,
        cross_section=xs
    )
    bot_out.connect("o1", bot_bend.ports["o2"])

    return c

# Create and save the component
if __name__ == "__main__":
    c = device_recreation()
    c.show() # Opens in KLayout if installed
    c.write_gds("trident_coupler.gds")