import gdsfactory as gf

@gf.cell
def custom_s_coupler():
    """
    Recreates the S-bend coupler geometry from the provided image.

    The device consists of two parallel waveguides that diverge at both ends
    using S-bends, and include short straight sections at the input/output ports.
    The overall footprint is 120um x 4um.
    """
    c = gf.Component("custom_s_coupler")
    
    # Device footprint parameters (from constraints)
    total_length = 120.0 # um
    total_height = 4.0   # um

    # Waveguide and internal spacing parameters
    wg_width = 0.8       # Waveguide core width
    gap_center = 0.2     # Gap between the two inner straight waveguide sections

    # Lengths of the different segments
    L_port_straight = 5.0    # Length of the straight segment at each input/output port
    L_straight_middle = 40.0 # Length of the parallel straight section in the middle
    
    # Calculate the horizontal length (dx) for each S-bend
    # total_length = (2 * L_port_straight) + (2 * L_bend) + L_straight_middle
    L_bend = (total_length - (2 * L_port_straight) - L_straight_middle) / 2
    
    if L_bend < 0:
        raise ValueError("Calculated L_bend is negative. Adjust length parameters.")

    # Calculate y-coordinates for the center of waveguides at ports and in the middle
    # Assuming the device is centered at (0,0) in the Y-axis.
    # For ports: (total_height / 2) - (wg_width / 2)
    y_port_center_offset = (total_height - wg_width) / 2 
    
    # For middle straight sections: (gap_center / 2) + (wg_width / 2)
    y_straight_center_offset = (gap_center / 2) + (wg_width / 2)
    
    # Calculate the vertical displacement (dy) for the S-bends
    dy_bend = y_port_center_offset - y_straight_center_offset

    # Define the waveguide cross-section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # --- Construct the Top Waveguide Path ---
    # Components are added sequentially and connected
    # 1. Input Straight
    straight_top_in = c << gf.components.straight(length=L_port_straight, cross_section=xs)
    
    # 2. First S-bend (bends inwards, so dy is negative for the top path)
    bend_s_top_in = c << gf.components.bend_s(size=(L_bend, -dy_bend), cross_section=xs)
    
    # 3. Middle Straight
    straight_top_middle = c << gf.components.straight(length=L_straight_middle, cross_section=xs)
    
    # 4. Second S-bend (bends outwards, so dy is positive for the top path)
    bend_s_top_out = c << gf.components.bend_s(size=(L_bend, dy_bend), cross_section=xs)
    
    # 5. Output Straight
    straight_top_out = c << gf.components.straight(length=L_port_straight, cross_section=xs)

    # Connect the components to form the top waveguide
    bend_s_top_in.connect("o1", straight_top_in.ports["o2"])
    straight_top_middle.connect("o1", bend_s_top_in.ports["o2"])
    bend_s_top_out.connect("o1", straight_top_middle.ports["o2"])
    straight_top_out.connect("o1", bend_s_top_out.ports["o2"])

    # Position the entire top waveguide path
    # The 'o1' port of the first straight segment (straight_top_in) is moved
    # to the desired start point of the top waveguide.
    straight_top_in.move(
        (-total_length / 2, y_port_center_offset)
    )

    # --- Construct the Bottom Waveguide Path ---
    # This path is a vertical mirror of the top path, so dy_bend signs are opposite.
    
    # 1. Input Straight
    straight_bottom_in = c << gf.components.straight(length=L_port_straight, cross_section=xs)
    
    # 2. First S-bend (bends inwards, so dy is positive for the bottom path)
    bend_s_bottom_in = c << gf.components.bend_s(size=(L_bend, dy_bend), cross_section=xs)
    
    # 3. Middle Straight
    straight_bottom_middle = c << gf.components.straight(length=L_straight_middle, cross_section=xs)
    
    # 4. Second S-bend (bends outwards, so dy is negative for the bottom path)
    bend_s_bottom_out = c << gf.components.bend_s(size=(L_bend, -dy_bend), cross_section=xs)
    
    # 5. Output Straight
    straight_bottom_out = c << gf.components.straight(length=L_port_straight, cross_section=xs)

    # Connect the components to form the bottom waveguide
    bend_s_bottom_in.connect("o1", straight_bottom_in.ports["o2"])
    straight_bottom_middle.connect("o1", bend_s_bottom_in.ports["o2"])
    bend_s_bottom_out.connect("o1", straight_bottom_middle.ports["o2"])
    straight_bottom_out.connect("o1", bend_s_bottom_out.ports["o2"])

    # Position the entire bottom waveguide path
    straight_bottom_in.move(
        (-total_length / 2, -y_port_center_offset)
    )

    # --- Expose the input/output ports for the overall component ---
    c.add_port("o1", port=straight_top_in.ports["o1"])    # Top-left input
    c.add_port("o2", port=straight_bottom_in.ports["o1"]) # Bottom-left input
    c.add_port("o3", port=straight_top_out.ports["o2"])   # Top-right output
    c.add_port("o4", port=straight_bottom_out.ports["o2"])# Bottom-right output

    return c

# Example usage and verification
if __name__ == "__main__":
    device = custom_s_coupler()
    
    # Verify the bounding box against the footprint constraint [120, 4]
    bbox = device.bbox()
    print(f"Component bounding box: {bbox}")
    # Expected bbox: [[-60.0, -2.0], [60.0, 2.0]], which corresponds to width=120, height=4.
    
    # Uncommented: This line will now save the GDS file.
    device.write_gds("custom_s_coupler.gds") 

    # Uncommented: This line will open the GDS in KLayout (if installed and configured)
    device.show()