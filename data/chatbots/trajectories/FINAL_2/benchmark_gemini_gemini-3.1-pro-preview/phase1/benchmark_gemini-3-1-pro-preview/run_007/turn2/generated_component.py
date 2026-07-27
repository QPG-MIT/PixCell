import gdsfactory as gf

@gf.cell
def optical_splitter_1x4_proportional():
    """
    Creates a 1x4 optical splitter with corrected visual proportions 
    to match the reference image.
    """
    c = gf.Component("optical_splitter_1x4")
    layer = (1, 0)
    
    # --- 1. Central Body (MMI Region) ---
    # Footprint constraint: 25 wide, 10 high.
    body_width = 25.0
    body_height = 10.0
    c << gf.components.rectangle(size=(body_width, body_height), layer=layer, centered=True)

    # --- 2. Bottom Input Taper ---
    # Proportions adjusted: base width is moderate, tapering down slightly.
    t_bot = c << gf.components.taper(
        length=6.0,
        width1=4.0,  # Base width at MMI body
        width2=1.5   # Input waveguide width
    )
    # Rotate to face UP and move to the bottom edge of the central rectangle
    t_bot.rotate(-90)
    t_bot.move((0, -body_height / 2))
    
    c.add_port("o1", port=t_bot.ports["o2"])

    # --- 3. Top Output Arms (Taper + Straight) ---
    # Symmetrically distributed centers
    x_centers = [-9.0, -3.0, 3.0, 9.0]
    
    # Top straight sections are thinner in the reference image
    top_arm_width = 0.5 
    xs_top = gf.cross_section.cross_section(width=top_arm_width, layer=layer)

    for i, x_pos in enumerate(x_centers):
        # A. Output Taper - (FIXED: narrower base, narrower tip, longer length)
        t_top = c << gf.components.taper(
            length=15.0,         # Increased length for the elongated look
            width1=2.0,          # Narrower base to create wider visual gaps
            width2=top_arm_width # Narrow tip merging into straight section
        )
        t_top.rotate(90)
        t_top.move((x_pos, body_height / 2))

        # B. Straight Extension - (FIXED: explicitly longer)
        s_top = c << gf.components.straight(
            length=10.0, 
            cross_section=xs_top
        )
        # Snap the straight section to the narrow end of the taper
        s_top.connect("o1", t_top.ports["o2"])
        
        c.add_port(f"o{i+2}", port=s_top.ports["o2"])

    return c

if __name__ == "__main__":
    device = optical_splitter_1x4_proportional()
    
    # Save the GDS file
    device.write_gds("optical_splitter_1x4.gds")