import gdsfactory as gf

@gf.cell
def directional_coupler_bent():
    c = gf.Component()

    # Dimensions derived from the footprint constraint [18, 3]
    length = 18.0
    total_height = 3.0
    
    # Tuned geometric parameters
    # Increased width to 1.0 to match the visual density of the target
    # Decreased gap to 0.2 to match the tight coupling pinch point
    wg_width = 1.0
    min_gap = 0.2
    
    # Define cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # Calculate Geometry
    half_length = length / 2.0

    # Vertical positioning to fill the 3.0um height constraint
    # Max Y = 1.5, Min Y = -1.5
    
    # --- Top Waveguide Calculations ---
    # Start Point (Input): Outer edge touches y=1.5
    # Center y = Edge - Width/2
    y_top_edge = total_height / 2.0
    y_start_top = y_top_edge - (wg_width / 2.0)  # 1.5 - 0.5 = 1.0
    
    # Middle Point (Waist): Inner edge touches y = min_gap/2
    # Center y = Edge + Width/2
    y_mid_gap_edge = min_gap / 2.0
    y_mid_top = y_mid_gap_edge + (wg_width / 2.0) # 0.1 + 0.5 = 0.6
    
    # Calculate vertical drop (dy) for the S-bend
    dy_top = y_mid_top - y_start_top  # 0.6 - 1.0 = -0.4

    # --- Construct Top Waveguide ---
    # Left Section: Converging S-bend (Input to Waist)
    tl = c << gf.components.bend_s(size=(half_length, dy_top), cross_section=xs)
    tl.move((0, y_start_top))

    # Right Section: Diverging S-bend (Waist to Output)
    tr = c << gf.components.bend_s(size=(half_length, -dy_top), cross_section=xs)
    tr.connect("o1", tl.ports["o2"])

    # --- Construct Bottom Waveguide ---
    # Symmetric values for bottom
    y_start_bot = -y_start_top
    dy_bot = -dy_top  # +0.4
    
    # Left Section
    bl = c << gf.components.bend_s(size=(half_length, dy_bot), cross_section=xs)
    bl.move((0, y_start_bot))

    # Right Section
    br = c << gf.components.bend_s(size=(half_length, -dy_bot), cross_section=xs)
    br.connect("o1", bl.ports["o2"])

    # --- Add External Ports ---
    c.add_port("o1", port=tl.ports["o1"])
    c.add_port("o2", port=bl.ports["o1"])
    c.add_port("o3", port=tr.ports["o2"])
    c.add_port("o4", port=br.ports["o2"])

    return c

if __name__ == "__main__":
    device = directional_coupler_bent()
    device.write_gds("directional_coupler_bent.gds")
    device.show()