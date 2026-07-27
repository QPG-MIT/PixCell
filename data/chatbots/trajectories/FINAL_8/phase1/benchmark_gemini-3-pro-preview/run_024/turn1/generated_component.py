import gdsfactory as gf

@gf.cell
def coupler_segmented_interaction():
    """
    Recreation of the segmented directional coupler based on the provided image.
    Footprint constraint: 120um x 4um.
    """
    c = gf.Component()

    # =======================================================================
    # Parameters
    # =======================================================================
    # Dimensions based on 120x4um footprint
    total_length = 120
    coupling_length = 60
    bend_length = (total_length - coupling_length) / 2  # 30um
    
    # Waveguide geometry parameters to fit 5 lines in the center
    wg_width = 0.3         # Width of the waveguides
    gap = 0.25             # Gap between waveguides
    pitch = wg_width + gap # Center-to-center distance
    
    # Y-coordinates for the "stack" of 5 lines in the center
    # 0 = Center floating line
    # +1 pitch = Upper floating line
    # -1 pitch = Lower floating line
    # +2 pitch = Top Arm (coupled section)
    # -2 pitch = Bottom Arm (coupled section)
    y_center_row_top = 2 * pitch
    y_center_row_bot = -2 * pitch
    
    # Y-coordinates for the Input/Output ports (outer edge of footprint)
    # We place inputs near y = +/- 1.5 to utilize the 4um height
    y_input_top = 1.5
    y_input_bot = -1.5
    
    # Calculate offset for the S-bends
    dy_top = y_center_row_top - y_input_top   # Negative value (going down)
    dy_bot = y_center_row_bot - y_input_bot   # Positive value (going up)

    # Define Cross Section
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # =======================================================================
    # 1. Central Floating Waveguides (Grating)
    # =======================================================================
    # We create 3 straight lines in the middle gap
    wg_float = gf.components.straight(length=coupling_length, cross_section=xs)
    
    # Middle line
    ref_mid = c << wg_float
    ref_mid.move((bend_length, 0))
    
    # Upper floating line
    ref_float_top = c << wg_float
    ref_float_top.move((bend_length, pitch))
    
    # Lower floating line
    ref_float_bot = c << wg_float
    ref_float_bot.move((bend_length, -pitch))

    # =======================================================================
    # 2. Top Arm Construction
    # =======================================================================
    # Component parts
    bend_s_in = gf.components.bend_s(size=(bend_length, dy_top), cross_section=xs)
    wg_arm = gf.components.straight(length=coupling_length, cross_section=xs)
    bend_s_out = gf.components.bend_s(size=(bend_length, -dy_top), cross_section=xs)

    # Place Top Input Bend
    t_in = c << bend_s_in
    t_in.move((0, y_input_top))

    # Place Top Straight Section (Connect to input bend)
    t_mid = c << wg_arm
    t_mid.connect("o1", t_in.ports["o2"])

    # Place Top Output Bend (Connect to straight section)
    t_out = c << bend_s_out
    t_out.connect("o1", t_mid.ports["o2"])

    # =======================================================================
    # 3. Bottom Arm Construction (Symmetric)
    # =======================================================================
    # Component parts (Note: dy is inverted compared to top)
    bend_s_in_bot = gf.components.bend_s(size=(bend_length, dy_bot), cross_section=xs)
    # Re-use straight wg_arm
    bend_s_out_bot = gf.components.bend_s(size=(bend_length, -dy_bot), cross_section=xs)

    # Place Bottom Input Bend
    b_in = c << bend_s_in_bot
    b_in.move((0, y_input_bot))

    # Place Bottom Straight Section
    b_mid = c << wg_arm
    b_mid.connect("o1", b_in.ports["o2"])

    # Place Bottom Output Bend
    b_out = c << bend_s_out_bot
    b_out.connect("o1", b_mid.ports["o2"])

    # =======================================================================
    # Ports
    # =======================================================================
    c.add_port("o1", port=t_in.ports["o1"])
    c.add_port("o2", port=b_in.ports["o1"])
    c.add_port("o3", port=t_out.ports["o2"])
    c.add_port("o4", port=b_out.ports["o2"])

    return c

# Create and save the device
device = coupler_segmented_interaction()
device.show() # View in KLayout
device.write_gds("segmented_coupler.gds")