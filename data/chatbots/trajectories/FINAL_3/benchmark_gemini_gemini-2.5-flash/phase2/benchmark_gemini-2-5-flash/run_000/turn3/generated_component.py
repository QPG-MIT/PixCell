import gdsfactory as gf

@gf.cell
def directional_coupler_from_image():
    """
    Recreates the directional coupler geometry from the provided image.

    The device consists of two parallel waveguides that approach each other
    with S-bends, run parallel for a coupling length, and then diverge again
    with S-bends.
    The overall footprint is 120um x 4um.
    """
    c = gf.Component("directional_coupler_from_image")
    
    # Device footprint parameters (from constraints)
    total_length = 120.0 # um
    total_height = 4.0   # um

    # Waveguide dimensions
    wg_width = 0.8       # Width of individual waveguides
    gap = 0.2            # Gap between the two waveguides in the parallel section
    
    # Lengths of sections
    L_io_straight = 10.0 # Length of straight segments at input/output ports
    L_coupler = 40.0     # Length of the parallel coupling region
    
    # Calculate horizontal length for each S-bend
    # total_length = 2 * L_io_straight + 2 * L_bend_s + L_coupler
    L_bend_s = (total_length - 2 * L_io_straight - L_coupler) / 2
    
    if L_bend_s < 0:
        raise ValueError("L_bend_s calculated negative. Adjust L_io_straight or L_coupler to fit footprint.")

    # Calculate Y-coordinates for the center of waveguides
    # At input/output: waveguides are at the outer edges of the total_height
    y_in_center = (total_height / 2) - (wg_width / 2) # = (4/2) - (0.8/2) = 2 - 0.4 = 1.6 um
    
    # In coupling region: waveguides are centered around y=0 with the specified gap
    y_coupler_center_top = (gap / 2) + (wg_width / 2)     # = (0.2/2) + (0.8/2) = 0.1 + 0.4 = 0.5 um
    y_coupler_center_bottom = -y_coupler_center_top       # = -0.5 um

    # Vertical displacement for each S-bend (distance to cover in Y)
    dy_bend_s = y_in_center - y_coupler_center_top # = 1.6 - 0.5 = 1.1 um

    if dy_bend_s < 0:
        raise ValueError("dy_bend_s calculated negative. Input waveguides are too close.")

    # Define waveguide cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 1. Input Straight Waveguides ---
    s_in_top = c << gf.components.straight(length=L_io_straight, cross_section=xs)
    s_in_bottom = c << gf.components.straight(length=L_io_straight, cross_section=xs)

    # Position input straights such that their 'o1' ports are at the leftmost edge
    s_in_top.move(origin=s_in_top.ports["o1"].center, destination=(-total_length / 2, y_in_center))
    s_in_bottom.move(origin=s_in_bottom.ports["o1"].center, destination=(-total_length / 2, -y_in_center))

    # --- 2. Input S-Bends ---
    # Top arm: moves from y_in_center (higher) to y_coupler_center_top (lower) -> negative dy
    bs_in_top = c << gf.components.bend_s(size=(L_bend_s, -dy_bend_s), cross_section=xs)
    # Bottom arm: moves from -y_in_center (lower) to y_coupler_center_bottom (higher) -> positive dy
    bs_in_bottom = c << gf.components.bend_s(size=(L_bend_s, dy_bend_s), cross_section=xs)

    bs_in_top.connect("o1", s_in_top.ports["o2"])
    bs_in_bottom.connect("o1", s_in_bottom.ports["o2"])

    # --- 3. Parallel Coupling Section ---
    coupler = c << gf.components.coupler_straight(length=L_coupler, gap=gap, cross_section=xs)

    # Connect S-bends to the coupler's input ports
    coupler.connect("o1", bs_in_top.ports["o2"])    # 'o1' is top input port of coupler
    coupler.connect("o2", bs_in_bottom.ports["o2"]) # 'o2' is bottom input port of coupler

    # --- 4. Output S-Bends ---
    # Top arm: moves from y_coupler_center_top (lower) to y_in_center (higher) -> positive dy
    bs_out_top = c << gf.components.bend_s(size=(L_bend_s, dy_bend_s), cross_section=xs)
    # Bottom arm: moves from y_coupler_center_bottom (higher) to -y_in_center (lower) -> negative dy
    bs_out_bottom = c << gf.components.bend_s(size=(L_bend_s, -dy_bend_s), cross_section=xs)

    # Connect coupler's output ports to the S-bends' input ports
    bs_out_top.connect("o1", coupler.ports["o3"])    # 'o3' is top output port of coupler
    bs_out_bottom.connect("o1", coupler.ports["o4"]) # 'o4' is bottom output port of coupler

    # --- 5. Output Straight Waveguides ---
    s_out_top = c << gf.components.straight(length=L_io_straight, cross_section=xs)
    s_out_bottom = c << gf.components.straight(length=L_io_straight, cross_section=xs)

    # Connect S-bends to the output straights
    s_out_top.connect("o1", bs_out_top.ports["o2"])
    s_out_bottom.connect("o1", bs_out_bottom.ports["o2"])

    # --- Expose ports for the overall component ---
    c.add_port("o1_top_in", port=s_in_top.ports["o1"])
    c.add_port("o2_bottom_in", port=s_in_bottom.ports["o1"])
    c.add_port("o3_top_out", port=s_out_top.ports["o2"])
    c.add_port("o4_bottom_out", port=s_out_bottom.ports["o2"])

    return c

# Example usage and verification
if __name__ == "__main__":
    device = directional_coupler_from_image()
    
    # Verify the bounding box against the footprint constraint [120, 4]
    bbox = device.bbox()
    print(f"Component bounding box: {bbox}")
    
    # Expected bbox: [[-60.0, -2.0], [60.0, 2.0]], which corresponds to width=120, height=4.
    # The actual bbox will be calculated by gdsfactory, and should match the target.
    # We carefully designed the x and y ranges to fit the 120x4 footprint.
    
    # Write the GDS file
    device.write_gds("directional_coupler_from_image.gds") 

    # Show the GDS layout (requires KLayout installation)
    device.show()