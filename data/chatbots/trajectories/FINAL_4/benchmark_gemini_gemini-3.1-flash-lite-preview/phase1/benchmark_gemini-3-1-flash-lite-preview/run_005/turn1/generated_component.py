import gdsfactory as gf

@gf.cell
def waveguide_coupler():
    c = gf.Component()
    
    # Define a default cross-section for the waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # Footprint analysis: 
    # Total length = 18um. We split this into two 9um S-bends.
    # Total height = 3um. We use a vertical displacement (dy) that ensures 
    # a tight gap in the center.
    dx = 9.0
    dy = 0.6 # This creates a total S-bend height of 0.6um
    
    # --- Top Waveguide ---
    # Segment 1: Curve from outer to inner gap
    top_s1 = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    # Segment 2: Curve from inner gap back to outer
    top_s2 = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    
    # Connect the segments
    top_s2.connect("o1", top_s1.ports["o2"])

    # --- Bottom Waveguide ---
    # Segment 1: Curve from outer to inner gap (opposite direction)
    bot_s1 = c << gf.components.bend_s(size=(dx, dy), cross_section=xs)
    # Segment 2: Curve from inner gap back to outer
    bot_s2 = c << gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    
    # Position the bottom waveguide below the top one
    # We move them by -1.5um to center them relative to the device origin
    bot_s1.movey(-1.5)
    bot_s2.movey(-1.5)
    
    # Connect the segments
    bot_s2.connect("o1", bot_s1.ports["o2"])

    # Add external ports for connectivity
    c.add_port("o1_top", port=top_s1.ports["o1"])
    c.add_port("o2_top", port=top_s2.ports["o2"])
    c.add_port("o1_bot", port=bot_s1.ports["o1"])
    c.add_port("o2_bot", port=bot_s2.ports["o2"])

    return c

# Create and save the component
device = waveguide_coupler()
device.write_gds("waveguide_coupler.gds")