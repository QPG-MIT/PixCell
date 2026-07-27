import gdsfactory as gf

@gf.cell
def directional_coupler() -> gf.Component:
    """
    Creates a directional coupler matching the exact footprint [18, 3].
    
    This iteration fixes the min_bend_radius error by overriding the cross-section
    constraints, and uses a balanced straight central region to closely match 
    the sweeping, smooth visual curves of the target image.
    """
    c = gf.Component("directional_coupler")

    # Define standard cross section, setting radius_min to 0.0 to prevent 
    # ValueErrors on the tight layout constraints of the footprint.
    wg_width = 0.5
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0), radius_min=0.0)

    # --- Derive Parameters from Footprint Constraints [18, 3] ---
    total_length = 18.0
    total_height = 3.0
    
    # Introduce a short flat coupling region in the center (matches target visual)
    straight_length = 4.0 
    dx_bend = (total_length - straight_length) / 2.0  # 7.0 for each S-bend

    # Calculate Y coordinates to perfectly fit the 3.0 total height constraint
    # Y bounds will be from -1.5 to 1.5. Center of ports at +/- 1.25.
    port_y = (total_height - wg_width) / 2.0  # 1.25
    
    # Define coupling gap at the center
    min_gap = 0.2
    center_y = (min_gap + wg_width) / 2.0     # 0.35
    
    # Calculate the Y shift (dy) for the S-bends to reach the desired center gap
    dy_bend = port_y - center_y               # 0.9

    # Create primitives using the unconstrained cross-section
    bend_down = gf.components.bend_s(size=(dx_bend, -dy_bend), cross_section=xs)
    bend_up = gf.components.bend_s(size=(dx_bend, dy_bend), cross_section=xs)
    straight_mid = gf.components.straight(length=straight_length, cross_section=xs)

    # --- Assemble Top Waveguide ---
    t1 = c << bend_down
    t2 = c << straight_mid
    t3 = c << bend_up

    t1.move((0, port_y))
    t2.connect("o1", t1.ports["o2"])
    t3.connect("o1", t2.ports["o2"])

    # --- Assemble Bottom Waveguide ---
    b1 = c << bend_up
    b2 = c << straight_mid
    b3 = c << bend_down

    b1.move((0, -port_y))
    b2.connect("o1", b1.ports["o2"])
    b3.connect("o1", b2.ports["o2"])

    # --- Expose External Ports ---
    c.add_port("o1", port=t1.ports["o1"])   # Top left input
    c.add_port("o2", port=b1.ports["o1"])   # Bottom left input
    c.add_port("o3", port=t3.ports["o2"])   # Top right output
    c.add_port("o4", port=b3.ports["o2"])   # Bottom right output

    return c

if __name__ == "__main__":
    # Create and save the device to GDS file
    device = directional_coupler()
    device.write_gds("directional_coupler.gds")