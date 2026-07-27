import gdsfactory as gf

@gf.cell
def device_mmi_1x4_fixed_ports():
    """
    Refined 1x4 MMI device geometry - Iteration 3 (Port Mismatch Fixed).
    
    Fixes:
    - Resolved PortWidthMismatchError by ensuring the taper's cross_section matches the connecting straight waveguide's width.
    - Defined explicit cross_sections for different widths to ensure layer and port consistency.
    
    Geometry:
    - Body: 25x10 um (Constraint).
    - Top Fingers: Composite (Taper + Straight).
      - Base width: 4.2um (High fill factor).
      - Tip/Straight width: 2.0um.
      - Uses a cross_section of width 2.0um to match the connection interface.
    - Bottom Finger:
      - Base width: 5.0um.
      - Tip width: 1.8um.
    """
    c = gf.Component("MMI_1x4_Corrected")

    # 1. Define Dimensions
    body_width = 25.0
    body_height = 10.0
    
    # Top Finger Geometry
    tf_taper_len = 4.0
    tf_straight_len = 12.0
    tf_width_base = 4.2
    tf_width_tip = 2.0
    
    # Bottom Finger Geometry
    bf_length = 6.0
    bf_width_base = 5.0
    bf_width_tip = 1.8

    # 2. Define Cross Sections
    # Cross-section for the top straight waveguides (and taper end)
    # Width 2.0 matches tf_width_tip
    xs_top = gf.cross_section.cross_section(width=tf_width_tip, layer=(1, 0))
    
    # Cross-section for the bottom taper (and general use)
    # Width matches the tip of the bottom taper to ensure correct port definition if needed
    xs_bot = gf.cross_section.cross_section(width=bf_width_tip, layer=(1, 0))

    # 3. Create the Central Body
    body = c << gf.components.rectangle(
        size=(body_width, body_height), 
        layer=(1, 0), 
        centered=True
    )

    # 4. Create Custom Composite Top Finger
    def create_finger():
        cmp = gf.Component()
        
        # Taper section
        # We pass xs_top (width=2.0). 
        # width1=4.2 overrides start geometry.
        # width2=2.0 matches xs_top width, ensuring Port o2 is 2.0um.
        taper = cmp << gf.components.taper(
            length=tf_taper_len,
            width1=tf_width_base,
            width2=tf_width_tip,
            cross_section=xs_top
        )
        
        # Straight section
        # Uses xs_top (width=2.0). Port o1 is 2.0um.
        straight = cmp << gf.components.straight(
            length=tf_straight_len,
            cross_section=xs_top
        )
        
        # Connect straight section to end of taper
        # Now 2.0um connects to 2.0um -> Success.
        straight.connect("o1", taper.ports["o2"])
        
        # Expose base port (width 4.2)
        cmp.add_port("o1", port=taper.ports["o1"])
        return cmp

    finger_cmp = create_finger()

    # Positions: Centers at ±3.125, ±9.375
    offsets = [3.125, 9.375]
    x_positions = [-x for x in reversed(offsets)] + offsets

    for x in x_positions:
        ref = c << finger_cmp
        ref.rotate(90)
        # Connect base of finger to top edge of body
        ref.move((x, body_height / 2))

    # 5. Create and Place Bottom Finger
    # Taper from 5.0 (base) to 1.8 (tip)
    taper_bot = gf.components.taper(
        length=bf_length,
        width1=bf_width_base,
        width2=bf_width_tip,
        cross_section=xs_bot
    )

    ref_bot = c << taper_bot
    ref_bot.rotate(-90)
    ref_bot.move((0, -body_height / 2))

    return c

if __name__ == "__main__":
    device = device_mmi_1x4_fixed_ports()
    device.write_gds("mmi_1x4_final.gds")
    print("GDS file generated successfully.")