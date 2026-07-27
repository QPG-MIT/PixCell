import gdsfactory as gf

@gf.cell
def smooth_coupler_like_device():
    """
    Creates a symmetric waveguide device with smooth S-bends and straight segments,
    resembling the target image.

    The device's dimensions are constrained by the footprint [120, 4] um.
    """
    c = gf.Component("smooth_coupler_like_device")

    # Define the default cross-section for the waveguides
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
    waveguide_width = xs.width

    # Device footprint dimensions
    full_length = 120.0
    full_height = 4.0

    # Calculate Y-coordinates for the centerlines of the waveguides
    # Outer (input/output) waveguides centerlines
    y_center_outer_top = full_height - waveguide_width / 2  # 3.75 um
    y_center_outer_bottom = waveguide_width / 2             # 0.25 um

    # Inner (middle) waveguides centerlines
    # Based on visual, assuming a physical gap of 0.2um in the middle
    physical_gap_inner = 0.2
    gap_inner_cc = physical_gap_inner + waveguide_width     # 0.7 um center-to-center
    y_center_inner_top = full_height / 2 + gap_inner_cc / 2 # 2.35 um
    y_center_inner_bottom = full_height / 2 - gap_inner_cc / 2 # 1.65 um

    # Horizontal lengths for different sections
    L_straight_io = 10.0      # Length of the straight input/output sections
    L_straight_middle = 10.0  # Length of the parallel straight section in the middle
    
    # Calculate horizontal length of the S-bend sections
    # Remaining length after input/output and middle straight sections
    remaining_length = full_length - (2 * L_straight_io) - L_straight_middle
    L_s_bend_h = remaining_length / 2.0 # Horizontal projection for ONE S-bend segment

    if L_s_bend_h <= 0:
        raise ValueError("Calculated S-bend horizontal length is zero or negative. Adjust L_straight_io or L_straight_middle.")

    # --- Construct Top Waveguide ---
    # 1. Input Straight
    wg_in_top = c << gf.components.straight(length=L_straight_io, cross_section=xs)
    wg_in_top.movey(y_center_outer_top) # Place the first component
    c.add_port("o1_top", port=wg_in_top.ports["o1"])

    # 2. Inward S-bend (connecting outer-top to inner-top)
    dy_in_top = y_center_inner_top - y_center_outer_top # (2.35 - 3.75 = -1.4)
    s_bend_in_top = c << gf.components.bend_s(size=(L_s_bend_h, dy_in_top), cross_section=xs)
    s_bend_in_top.connect("o1", wg_in_top.ports["o2"])

    # 3. Middle Straight
    wg_middle_top = c << gf.components.straight(length=L_straight_middle, cross_section=xs)
    wg_middle_top.connect("o1", s_bend_in_top.ports["o2"])

    # 4. Outward S-bend (connecting inner-top to outer-top)
    dy_out_top = y_center_outer_top - y_center_inner_top # (3.75 - 2.35 = 1.4)
    s_bend_out_top = c << gf.components.bend_s(size=(L_s_bend_h, dy_out_top), cross_section=xs)
    s_bend_out_top.connect("o1", wg_middle_top.ports["o2"])

    # 5. Output Straight
    wg_out_top = c << gf.components.straight(length=L_straight_io, cross_section=xs)
    wg_out_top.connect("o1", s_bend_out_top.ports["o2"])
    c.add_port("o2_top", port=wg_out_top.ports["o2"])


    # --- Construct Bottom Waveguide ---
    # 1. Input Straight
    wg_in_bottom = c << gf.components.straight(length=L_straight_io, cross_section=xs)
    wg_in_bottom.movey(y_center_outer_bottom) # Place the first component
    c.add_port("o1_bottom", port=wg_in_bottom.ports["o1"])

    # 2. Inward S-bend (connecting outer-bottom to inner-bottom)
    dy_in_bottom = y_center_inner_bottom - y_center_outer_bottom # (1.65 - 0.25 = 1.4)
    s_bend_in_bottom = c << gf.components.bend_s(size=(L_s_bend_h, dy_in_bottom), cross_section=xs)
    s_bend_in_bottom.connect("o1", wg_in_bottom.ports["o2"])

    # 3. Middle Straight
    wg_middle_bottom = c << gf.components.straight(length=L_straight_middle, cross_section=xs)
    wg_middle_bottom.connect("o1", s_bend_in_bottom.ports["o2"])

    # 4. Outward S-bend (connecting inner-bottom to outer-bottom)
    dy_out_bottom = y_center_outer_bottom - y_center_inner_bottom # (0.25 - 1.65 = -1.4)
    s_bend_out_bottom = c << gf.components.bend_s(size=(L_s_bend_h, dy_out_bottom), cross_section=xs)
    s_bend_out_bottom.connect("o1", wg_middle_bottom.ports["o2"])

    # 5. Output Straight
    wg_out_bottom = c << gf.components.straight(length=L_straight_io, cross_section=xs)
    wg_out_bottom.connect("o1", s_bend_out_bottom.ports["o2"])
    c.add_port("o2_bottom", port=wg_out_bottom.ports["o2"])

    return c

# Example usage and visualization
if __name__ == "__main__":
    device = smooth_coupler_like_device()
    device.show() # Renders the device for visualization in a GDS viewer
    device.write_gds("smooth_coupler_like_device.gds") # Saves the GDS file