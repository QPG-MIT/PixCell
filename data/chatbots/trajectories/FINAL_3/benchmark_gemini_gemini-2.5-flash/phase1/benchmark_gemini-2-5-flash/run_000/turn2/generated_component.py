import gdsfactory as gf

@gf.cell
def custom_y_combiner():
    """
    Recreates the Y-combiner geometry from the provided image.

    The device consists of two parallel input waveguides that smoothly merge
    into a single wider output waveguide.
    The overall footprint is 120um x 4um.
    """
    c = gf.Component("custom_y_combiner")
    
    # Device footprint parameters (from constraints)
    total_length = 120.0 # um
    total_height = 4.0   # um

    # Waveguide dimensions
    wg_width_in = 0.8    # Width of the input waveguides
    wg_width_out = 2.0   # Width of the output waveguide (visibly wider)
    
    # Lengths of straight sections
    L_port_in = 15.0     # Length of the straight segment at each input port
    L_port_out = 30.0    # Length of the straight segment at the output port
    
    # Calculate Y-coordinates for the center of input waveguides
    # Assuming the device is centered at (0,0) in the Y-axis.
    y_in_center_offset = (total_height - wg_width_in) / 2 # = (4 - 0.8) / 2 = 1.6 um

    # Calculate horizontal and vertical dimensions for the merging section
    L_merge_section = total_length - L_port_in - L_port_out # = 120 - 15 - 30 = 75 um

    # Split the merge section length between the S-bend and the taper
    L_bend_s = L_merge_section * 0.55 # Horizontal length for the S-bend curve
    L_taper = L_merge_section * 0.45  # Horizontal length for the taper section
                                        
    # The S-bend brings the waveguide from y_in_center_offset to the point where
    # the taper starts, which should be centered at half of the output waveguide's total width.
    # The end of each taper (width = wg_width_out / 2) will be centered at +/- (wg_width_out / 4).
    # This means the top taper ends at y=0.5 and bottom at y=-0.5, each with width 1.0.
    y_taper_start_center = wg_width_out / 4 # = 2.0 / 4 = 0.5 um

    # Calculate the vertical displacement for the S-bends
    dy_bend_s = y_in_center_offset - y_taper_start_center # = 1.6 - 0.5 = 1.1 um

    # Define waveguide cross-sections
    xs_in = gf.cross_section.cross_section(width=wg_width_in, layer=(1, 0))
    xs_out = gf.cross_section.cross_section(width=wg_width_out, layer=(1, 0))

    # --- Create Input Straight Waveguides ---
    s_in_top = c << gf.components.straight(length=L_port_in, cross_section=xs_in)
    s_in_bottom = c << gf.components.straight(length=L_port_in, cross_section=xs_in)

    # Position input straights
    s_in_top.move(destination=(-total_length / 2, y_in_center_offset), origin=s_in_top.ports["o1"].center)
    s_in_bottom.move(destination=(-total_length / 2, -y_in_center_offset), origin=s_in_bottom.ports["o1"].center)

    # --- Create Output Straight Waveguide ---
    s_out = c << gf.components.straight(length=L_port_out, cross_section=xs_out)
    # Position output straight: its 'o1' port at the start of the output section
    # The merge point occurs at x = L_port_in + L_bend_s + L_taper - total_length/2
    x_merge_start_for_output = s_in_top.ports["o2"].x + L_bend_s + L_taper
    s_out.move(destination=(x_merge_start_for_output, 0), origin=s_out.ports["o1"].center)


    # --- Create Merging Arms (S-bend + Taper) ---
    # Top Arm
    bs_top = c << gf.components.bend_s(size=(L_bend_s, -dy_bend_s), cross_section=xs_in) # -dy for top arm to move downwards
    taper_top = c << gf.components.taper(
        length=L_taper, width1=wg_width_in, width2=wg_width_out / 2, cross_section=xs_in
    )

    # Connect top arm components
    bs_top.connect("o1", s_in_top.ports["o2"])
    taper_top.connect("o1", bs_top.ports["o2"])

    # Bottom Arm (Symmetrical)
    bs_bottom = c << gf.components.bend_s(size=(L_bend_s, dy_bend_s), cross_section=xs_in) # +dy for bottom arm to move upwards
    taper_bottom = c << gf.components.taper(
        length=L_taper, width1=wg_width_in, width2=wg_width_out / 2, cross_section=xs_in
    )

    # Connect bottom arm components
    bs_bottom.connect("o1", s_in_bottom.ports["o2"])
    taper_bottom.connect("o1", bs_bottom.ports["o2"])

    # --- Boolean Operation to Merge Tapers ---
    # The two tapers meet at the center line (y=0) and their 'width2' values
    # sum up to the total output width (wg_width_out = 2.0).
    # gf.boolean takes component references and returns a new component containing the boolean result.
    merged_shape_comp = gf.boolean(
        taper_top, taper_bottom, operation="or", layer=(1,0)
    )
    # Add the result of the boolean operation to the main component
    c << merged_shape_comp
    
    # --- Expose ports for the overall component ---
    c.add_port("o1_top", port=s_in_top.ports["o1"])
    c.add_port("o2_bottom", port=s_in_bottom.ports["o1"])
    c.add_port("o3_out", port=s_out.ports["o2"])

    return c

# Example usage and verification
if __name__ == "__main__":
    device = custom_y_combiner()
    
    # Verify the bounding box against the footprint constraint [120, 4]
    bbox = device.bbox()
    print(f"Component bounding box: {bbox}")
    # Expected bbox: [[-60.0, -2.0], [60.0, 2.0]], which corresponds to width=120, height=4.
    
    # Write the GDS file
    device.write_gds("custom_y_combiner.gds") 

    # Show the GDS layout (requires KLayout installation)
    device.show()