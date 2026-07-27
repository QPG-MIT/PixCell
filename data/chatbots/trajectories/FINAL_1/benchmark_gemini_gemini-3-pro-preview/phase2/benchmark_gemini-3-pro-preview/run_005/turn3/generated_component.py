import gdsfactory as gf

@gf.cell
def device_recreation_refined_v2():
    """
    Refined recreation of the trident spot-size converter matching the visual weight
    and aspect ratios of the target image.
    
    Adjustments:
    - Reduced waveguide width and increased gap visibility to match image contrast.
    - Constrained total input height to exactly 1.7um.
    - Aligned taper termination with the onset of the S-bends.
    """
    c = gf.Component()
    
    # --- Dimensions & constraints ---
    # Footprint constraint: 40.0um length, 1.7um height
    
    # Longitudinal sections (Total 40.0)
    len_taper = 19.0       # Length of the input straight/taper section
    len_bend = 16.0        # Length of the S-bend section
    len_out = 5.0          # Length of the output straight section
    
    # Transverse dimensions
    # Input Constraint: 3*w_in + 2*gap_in = 1.7
    w_in = 0.42            # Input width (balanced for visual weight)
    gap_in = 0.22          # Input gap (wide enough to be clearly visible)
    
    w_out = 0.38           # Output width (slightly narrower than input)
    gap_out = 0.30         # Output gap (wider than input gap, distinct separation)
    w_tip = 0.04           # Sharp tip width for middle taper
    
    # --- Calculations ---
    
    # 1. Pitch Calculations (Center-to-Center distances)
    # Input Pitch: Distance from center (y=0) to center of top arm
    # y = (middle_half_width) + gap + (top_half_width)
    y_in_pitch = (w_in / 2) + gap_in + (w_in / 2)
    
    # Output Pitch: Distance from center (y=0) to center of top output arm
    y_out_pitch = (gap_out / 2) + (w_out / 2)
    
    # Vertical Shift required for the S-bend
    # The top arm moves down (negative shift), bottom moves up
    dy = y_in_pitch - y_out_pitch

    # Cross-section for the S-bend and output (using the output width)
    xs_out = gf.cross_section.cross_section(width=w_out, layer=(1, 0))

    # --- Geometry Construction ---

    # 1. Middle Arm
    # Tapers from w_in to a fine point (w_tip)
    middle_taper = c << gf.components.taper(
        length=len_taper,
        width1=w_in,
        width2=w_tip,
        layer=(1, 0)
    )
    # Defaults to starting at (0,0)

    # 2. Top Arm
    # Section A: Straight Taper (Width reduces slightly from w_in to w_out)
    # This creates the subtle narrowing effect before the bend.
    top_straight = c << gf.components.taper(
        length=len_taper,
        width1=w_in,
        width2=w_out,
        layer=(1, 0)
    )
    top_straight.move((0, y_in_pitch))

    # Section B: S-Bend (Shifts y position inwards)
    # size = (length, y_shift). Top arm shifts DOWN, so y is negative.
    top_bend = c << gf.components.bend_s(
        size=(len_bend, -dy), 
        cross_section=xs_out
    )
    top_bend.connect("o1", top_straight.ports["o2"])

    # Section C: Straight Output
    top_out = c << gf.components.straight(
        length=len_out,
        cross_section=xs_out
    )
    top_out.connect("o1", top_bend.ports["o2"])

    # 3. Bottom Arm (Mirrored)
    # Section A: Straight Taper
    bot_straight = c << gf.components.taper(
        length=len_taper,
        width1=w_in,
        width2=w_out,
        layer=(1, 0)
    )
    bot_straight.move((0, -y_in_pitch))

    # Section B: S-Bend (Shifts UP, so y is positive)
    bot_bend = c << gf.components.bend_s(
        size=(len_bend, dy), 
        cross_section=xs_out
    )
    bot_bend.connect("o1", bot_straight.ports["o2"])

    # Section C: Straight Output
    bot_out = c << gf.components.straight(
        length=len_out,
        cross_section=xs_out
    )
    bot_out.connect("o1", bot_bend.ports["o2"])

    return c

if __name__ == "__main__":
    c = device_recreation_refined_v2()
    c.show()
    c.write_gds("trident_refined_v2.gds")