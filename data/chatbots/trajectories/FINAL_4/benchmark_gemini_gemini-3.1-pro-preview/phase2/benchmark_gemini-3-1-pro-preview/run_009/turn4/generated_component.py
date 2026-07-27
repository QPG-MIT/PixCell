import gdsfactory as gf

@gf.cell
def smooth_directional_coupler() -> gf.Component:
    """
    Parametric directional coupler with a continuous smooth curve.
    Total Footprint: 18um x 3um.
    """
    c = gf.Component("smooth_directional_coupler")

    # --- Geometric Parameters ---
    wg_width = 0.5
    gap = 0.2
    
    # Deriving coordinates for the exact [18, 3] bounding box
    # Outer width is 3.0. Centers of outer ports are 0.25um inside the edges.
    y_out = (3.0 - wg_width) / 2.0          # 1.25 um
    
    # Inner centers for the gap. 
    # Gap is between the inner edges: y_center_top - wg_width/2 - (y_center_bot + wg_width/2) = gap
    # 2 * y_in - wg_width = gap => y_in = (wg_width + gap) / 2
    y_in = (wg_width + gap) / 2.0           # 0.35 um
    
    dy = y_out - y_in                       # 0.9 um
    
    # Target image shows a continuous smooth curve without a prominent straight section.
    # We remove the straight section completely so the s-bends meet at a single point.
    dx = 18.0 / 2.0                         # 9.0 um

    # Create the standard cross-section
    xs = gf.cross_section.cross_section(
        width=wg_width, 
        layer=(1, 0)
    )

    # --- Component Primitives ---
    # S-bends to transition between port spacing and coupling gap
    bend_down = gf.components.bend_s(size=(dx, -dy), cross_section=xs)
    bend_up = gf.components.bend_s(size=(dx, dy), cross_section=xs)

    # ==========================
    # --- Top Arm Assembly ---
    # ==========================
    top_left = c << bend_down
    top_left.movey(y_out)
    
    # Connect upward bend directly to downward bend for a continuous cosine curve
    top_right = c << bend_up
    top_right.connect("o1", top_left.ports["o2"])

    # ==========================
    # --- Bottom Arm Assembly --
    # ==========================
    bot_left = c << bend_up
    bot_left.movey(-y_out)
    
    bot_right = c << bend_down
    bot_right.connect("o1", bot_left.ports["o2"])

    # --- Expose the external ports ---
    c.add_port("o1", port=top_left.ports["o1"])
    c.add_port("o2", port=bot_left.ports["o1"])
    c.add_port("o3", port=top_right.ports["o2"])
    c.add_port("o4", port=bot_right.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the component and explicitly write the GDS file
    c = smooth_directional_coupler()
    c.write_gds("smooth_directional_coupler.gds")