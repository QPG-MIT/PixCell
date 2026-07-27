import gdsfactory as gf

@gf.cell
def device_recreation_refined_v3():
    """
    Refined recreation of the trident spot-size converter matching the visual weight
    and aspect ratios of the target image.
    
    Improvements over previous iteration:
    - Extended the middle taper length significantly to overlap with the S-bend section,
      fixing the large gap artifact. The tip now terminates exactly where the outer arms
      finish converging.
    - Adjusted longitudinal segmentation: Shorter initial straight section, longer smooth bend.
    - Maintained exact 1.7um input height constraint.
    """
    c = gf.Component()
    
    # --- Dimensions & constraints ---
    # Footprint constraint: 40.0um length, 1.7um height
    
    # Longitudinal sections
    # Visually, the device has a straight start, a long converging bend, and a short straight output.
    # The middle taper extends through the straight and bend sections.
    len_straight = 12.0
    len_bend = 23.0
    len_out = 5.0
    # Total length = 40.0
    
    len_middle_taper = len_straight + len_bend  # 35.0um

    # Transverse dimensions
    # Input Constraint: 3*w_in + 2*gap_in = 1.7
    w_in = 0.42            # Input width
    gap_in = 0.22          # Input gap
    
    w_out = 0.38           # Output width (slight tapering of outer arms matches visual thinning)
    gap_out = 0.30         # Output gap (wider than input gap, creating distinct separation)
    w_tip = 0.03           # Sharp tip for middle taper
    
    # --- Calculations ---
    
    # 1. Pitch Calculations (Distance from y=0 to center of outer arm)
    # Input Side:
    # y = (half_middle_width) + gap + (half_outer_width)
    y_in_pitch = (w_in / 2) + gap_in + (w_in / 2)
    
    # Output Side:
    # y = (half_gap_out) + (half_outer_width)
    # Note: Middle waveguide is gone, so gap is strictly between the two outer arms.
    y_out_pitch = (gap_out / 2) + (w_out / 2)
    
    # Vertical Shift for S-bend
    dy = y_in_pitch - y_out_pitch

    # Cross-section for the bend and output sections (using w_out)
    xs_out = gf.cross_section.cross_section(width=w_out, layer=(1, 0))

    # --- Geometry Construction ---

    # 1. Middle Arm
    # Long taper from input width to fine tip. 
    # Extends to x=35.0, exactly where outer arms finish bending.
    middle_taper = c << gf.components.taper(
        length=len_middle_taper,
        width1=w_in,
        width2=w_tip,
        layer=(1, 0)
    )
    # Defaults to starting at (0,0)

    # 2. Top Arm
    # Section A: Straight Taper (w_in -> w_out)
    # Allows for subtle width reduction before the bend
    top_straight = c << gf.components.taper(
        length=len_straight,
        width1=w_in,
        width2=w_out,
        layer=(1, 0)
    )
    top_straight.move((0, y_in_pitch))

    # Section B: S-Bend (Shifts DOWN)
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
    # Section A: Straight Taper (w_in -> w_out)
    bot_straight = c << gf.components.taper(
        length=len_straight,
        width1=w_in,
        width2=w_out,
        layer=(1, 0)
    )
    bot_straight.move((0, -y_in_pitch))

    # Section B: S-Bend (Shifts UP)
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
    c = device_recreation_refined_v3()
    c.show()
    c.write_gds("trident_refined_v3.gds")