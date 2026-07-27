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
    # The total device height is 4.0um, so it spans from y=-2.0um to y=2.0um.
    # At input/output: the center of the top waveguide should be at y = (total_height/2 - wg_width/2)
    # i.e., 2.0 - 0.4 = 1.6um.
    # The center of the bottom waveguide will be at -1.6um.
    y_in_center = (total_height / 2) - (wg_width / 2) 
    
    # In coupling region: waveguides are centered around y=0 with the specified gap.
    # The gap is 0.2um. The total vertical space occupied by two waveguides and gap is 2*wg_width + gap.
    # The center of the top waveguide in the coupling region: (gap/2 + wg_width/2) = (0.1 + 0.4) = 0.5um
    # The center of the bottom waveguide in the coupling region: -(gap/2 + wg_width/2) = -0.5um
    y_coupler_center_top = (gap / 2) + (wg_width / 2)     
    y_coupler_center_bottom = -y_coupler_center_top       

    # Vertical displacement for each S-bend (distance to cover in Y)
    # This is the difference in Y-center between the input/output and coupling regions.
    dy_bend_s = y_in_center - y_coupler_center_top # = 1.6 - 0.5 = 1.1 um

    if dy_bend_s < 0:
        raise ValueError("dy_bend_s calculated negative. Input waveguides are too close, or coupler region too wide.")

    # Define waveguide cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- 1. Input Straight Waveguides ---
    s_in_top = c << gf.components.straight(length=L_io_straight, cross_section=xs)
    s_in_bottom = c << gf.components.straight(length=L_io_straight, cross_section=xs)

    # Position input straights such that their 'o1' ports are at the leftmost edge
    # The device will be centered at (0,0), so the leftmost edge is -total_length / 2
    x_start_device = -total_length / 2
    s_in_top.move(origin=s_in_top.ports["o1"].center, destination=(x_start_device, y_in_center))
    s_in_bottom.move(origin=s_in_bottom.ports["o1"].center, destination=(x_start_device, -y_in_center))

    # --- 2. Input S-Bends ---
    # Top arm: moves from y_in_center (higher) to y_coupler_center_top (lower) -> negative dy
    bs_in_top = c << gf.components.bend_s(size=(L_bend_s, -dy_bend_s), cross_section=xs)
    # Bottom arm: moves from -y_in_center (lower) to y_coupler_center_bottom (higher) -> positive dy
    bs_in_bottom = c << gf.components.bend_s(size=(L_bend_s, dy_bend_s), cross_section=xs)

    bs_in_top.connect("o1", s_in_top.ports["o2"])
    bs_in_bottom.connect("o1", s_in_bottom.ports["o2"])

    # --- 3. Parallel Coupling Section (Using two separate straight waveguides instead of coupler_straight) ---
    s_coupler_top = c << gf.components.straight(length=L_coupler, cross_section=xs)
    s_coupler_bottom = c << gf.components.straight(length=L_coupler, cross_section=xs)

    # Connect top coupling straight to the output of the top input S-bend
    s_coupler_top.connect("o1", bs_in_top.ports["o2"])
    # Connect bottom coupling straight to the output of the bottom input S-bend
    s_coupler_bottom.connect("o1", bs_in_bottom.ports["o2"])

    # --- 4. Output S-Bends ---
    # Top arm: moves from y_coupler_center_top (lower) to y_in_center (higher) -> positive dy
    bs_out_top = c << gf.components.bend_s(size=(L_bend_s, dy_bend_s), cross_section=xs)
    # Bottom arm: moves from y_coupler_center_bottom (higher) to -y_in_center (lower) -> negative dy
    bs_out_bottom = c << gf.components.bend_s(size=(L_bend_s, -dy_bend_s), cross_section=xs)

    # Connect input of output S-bends to the output of the coupling straights
    bs_out_top.connect("o1", s_coupler_top.ports["o2"])
    bs_out_bottom.connect("o1", s_coupler_bottom.ports["o2"])

    # --- 5. Output Straight Waveguides ---
    s_out_top = c << gf.components.straight(length=L_io_straight, cross_section=xs)
    s_out_bottom = c << gf.components.straight(length=L_io_straight, cross_section=xs)

    # Connect output straights to the output of the output S-bends
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
    
    # Expected bbox for a 120x4 component centered at (0,0) is [[-60.0, -2.0], [60.0, 2.0]]
    # The current calculations should result in this:
    # X-coords: starts at -60 (s_in), ends at -50.
    # S-bend in: starts at -50, ends at -50 + 30 = -20.
    # Coupler: starts at -20, ends at -20 + 40 = 20.
    # S-bend out: starts at 20, ends at 20 + 30 = 50.
    # S-out: starts at 50, ends at 50 + 10 = 60.
    # Total X-span = 60 - (-60) = 120.0
    # Y-coords: top waveguide outer edge at y=2.0, bottom waveguide outer edge at y=-2.0.
    # Total Y-span = 2.0 - (-2.0) = 4.0
    
    # Write the GDS file
    device.write_gds("directional_coupler_from_image.gds") 

    # Show the GDS layout (requires KLayout installation)
    # device.show()