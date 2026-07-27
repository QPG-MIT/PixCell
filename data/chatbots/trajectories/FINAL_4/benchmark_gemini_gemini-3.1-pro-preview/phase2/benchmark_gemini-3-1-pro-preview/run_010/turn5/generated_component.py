import gdsfactory as gf

@gf.cell
def directional_coupler() -> gf.Component:
    """
    Creates a directional coupler matching the exact footprint [18, 3].
    
    This iteration re-introduces a central straight section. The previous attempt 
    without it created too much of a "pinch" at the center. The target image clearly 
    shows a parallel "coupling region" where the waveguides run straight for a short 
    distance. We also slightly widen the waveguides and tighten the gap to better 
    match the visual weight of the reference image.
    """
    c = gf.Component("directional_coupler")

    # Tuned waveguide width for a bolder appearance closer to the reference
    wg_width = 0.7
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0), radius_min=0.0)

    # --- Derive Parameters from Footprint Constraints [18, 3] ---
    total_length = 18.0
    total_height = 3.0
    
    # Port Y centers to exactly fit the 3.0 total height constraint
    # (3.0 - 0.7) / 2 = 1.15
    port_y = (total_height - wg_width) / 2.0
    
    # Tighter coupling gap to match the visually narrow space in the center
    min_gap = 0.25
    # (0.25 + 0.7) / 2 = 0.475
    center_y = (min_gap + wg_width) / 2.0
    
    # Length of the parallel straight section in the middle
    L_straight = 5.0
    
    # Calculate dimensions for the S-bends to fill the remaining space
    dx_bend = (total_length - L_straight) / 2.0  # (18 - 5) / 2 = 6.5
    dy_bend = port_y - center_y                  # 1.15 - 0.475 = 0.675

    # Create primitives
    bend_down = gf.components.bend_s(size=(dx_bend, -dy_bend), cross_section=xs)
    bend_up = gf.components.bend_s(size=(dx_bend, dy_bend), cross_section=xs)
    straight_center = gf.components.straight(length=L_straight, cross_section=xs)

    # --- Assemble Top Waveguide ---
    t1 = c << bend_down
    t2 = c << straight_center
    t3 = c << bend_up

    # Position the start of the top arm at the correct port_y
    t1.move((0, port_y))
    t2.connect("o1", t1.ports["o2"])
    t3.connect("o1", t2.ports["o2"])

    # --- Assemble Bottom Waveguide ---
    b1 = c << bend_up
    b2 = c << straight_center
    b3 = c << bend_down

    # Position the start of the bottom arm at the correct -port_y
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