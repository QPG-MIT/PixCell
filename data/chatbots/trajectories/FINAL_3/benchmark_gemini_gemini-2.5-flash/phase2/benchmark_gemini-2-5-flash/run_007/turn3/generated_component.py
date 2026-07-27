import gdsfactory as gf

@gf.cell
def crossover_waveguides() -> gf.Component:
    """
    Recreates the geometry from the provided image showing two waveguides
    that approach each other, run parallel, and then diverge,
    using GDSFactory parametric functions.
    """
    c = gf.Component("crossover_waveguides")

    # Define the waveguide cross-section
    # Assuming a standard width of 0.5 um on layer (1, 0)
    xs_width = 0.5
    xs = gf.cross_section.cross_section(width=xs_width, layer=(1, 0))

    # --- Derived Parameters from Footprint [120, 4] um ---
    desired_final_x_span = 120  # The actual target footprint X dimension
    total_height = 4     # Total vertical height of the device

    # Observed implicit X-dimension scaling factor.
    # In the previous turn, NominalTotalX=80 resulted in ActualX=140.
    # So, SF = 140 / 80 = 1.75.
    x_dimension_scaling_factor = 1.75

    # The sum of individual segment lengths (L_in + dx_bend + L_center + dx_bend + L_out)
    # should add up to this value, which then gets scaled to the desired_final_x_span.
    internal_total_length_for_calc = desired_final_x_span / x_dimension_scaling_factor
    # internal_total_length_for_calc = 120 / 1.75 = 480 / 7 ≈ 68.5714 um

    # Calculate centerline Y-coordinates
    # Outermost Y for waveguide centerlines at the input/output ports.
    y_outer_centerline = (total_height / 2) - (xs_width / 2) # 2.0 - 0.25 = 1.75 um

    # Central Y for waveguide centerlines where they run parallel.
    # Assuming a gap between the waveguides in the middle equal to the waveguide width (0.5 um).
    # This means the centerlines are at +/- (half_gap + half_width) = +/- (0.25 + 0.25) = +/- 0.5 um.
    y_inner_centerline = xs_width # 0.5 um

    # Vertical displacement for each S-bend transition
    dy_bend = y_outer_centerline - y_inner_centerline # 1.75 - 0.5 = 1.25 um

    # Horizontal lengths for different sections to distribute internal_total_length_for_calc
    # Layout: L_in - dx_bend - L_center - dx_bend - L_out
    L_in = 10         # Length of input straight segments
    L_out = 10        # Length of output straight segments
    dx_bend = 20      # Horizontal length of each S-bend transition
    
    # Calculate L_center based on the adjusted internal_total_length_for_calc
    L_center = internal_total_length_for_calc - (2 * L_in) - (2 * dx_bend)
    # L_center = (480 / 7) - (2 * 10) - (2 * 20) = (480 / 7) - 20 - 40 = (480 / 7) - 60
    # L_center = (480 - 420) / 7 = 60 / 7 ≈ 8.5714 um

    # Ensure L_center is not negative. If it is, the fixed lengths (L_in, L_out, dx_bend) are too large.
    if L_center < 0:
        raise ValueError("Calculated L_center is negative. Adjust L_in, L_out, or dx_bend.")
    
    # --- Construct the top waveguide ---
    input_top = c << gf.components.straight(length=L_in, cross_section=xs)
    s_bend_top_in = c << gf.components.bend_s(size=(dx_bend, -dy_bend), cross_section=xs) # Negative dy to bend down
    center_top = c << gf.components.straight(length=L_center, cross_section=xs)
    s_bend_top_out = c << gf.components.bend_s(size=(dx_bend, dy_bend), cross_section=xs) # Positive dy to bend up
    output_top = c << gf.components.straight(length=L_out, cross_section=xs)

    # Connect segments for the top waveguide sequentially
    s_bend_top_in.connect("o1", input_top.ports["o2"])
    center_top.connect("o1", s_bend_top_in.ports["o2"])
    s_bend_top_out.connect("o1", center_top.ports["o2"])
    output_top.connect("o1", s_bend_top_out.ports["o2"])

    # Position the entire top waveguide assembly.
    # We center the component such that the overall span is desired_final_x_span.
    # The 'o1' port of input_top should be at (-desired_final_x_span/2, y_outer_centerline).
    input_top.movex(-desired_final_x_span / 2).movey(y_outer_centerline)

    # --- Construct the bottom waveguide ---
    input_bottom = c << gf.components.straight(length=L_in, cross_section=xs)
    s_bend_bottom_in = c << gf.components.bend_s(size=(dx_bend, dy_bend), cross_section=xs) # Positive dy to bend up
    center_bottom = c << gf.components.straight(length=L_center, cross_section=xs)
    s_bend_bottom_out = c << gf.components.bend_s(size=(dx_bend, -dy_bend), cross_section=xs) # Negative dy to bend down
    output_bottom = c << gf.components.straight(length=L_out, cross_section=xs)

    # Connect segments for the bottom waveguide sequentially
    s_bend_bottom_in.connect("o1", input_bottom.ports["o2"])
    center_bottom.connect("o1", s_bend_bottom_in.ports["o2"])
    s_bend_bottom_out.connect("o1", center_bottom.ports["o2"])
    output_bottom.connect("o1", s_bend_bottom_out.ports["o2"])

    # Position the entire bottom waveguide assembly.
    input_bottom.movex(-desired_final_x_span / 2).movey(-y_outer_centerline)

    # Add external ports to the main component for device interface.
    c.add_port("o1_top", port=input_top.ports["o1"])
    c.add_port("o1_bottom", port=input_bottom.ports["o1"])

    c.add_port("o2_top", port=output_top.ports["o2"])
    c.add_port("o2_bottom", port=output_bottom.ports["o2"])

    return c

if __name__ == "__main__":
    device = crossover_waveguides()
    device.write_gds("crossover_device.gds")

    bbox = device.bbox()
    x_span = bbox.right - bbox.left
    y_span = bbox.top - bbox.bottom

    expected_length = 120
    expected_height = 4

    # Using round to handle potential floating point inaccuracies in bbox calculations
    print(f"Calculated X span: {x_span:.3f} um (Expected: {expected_length} um)")
    print(f"Calculated Y span: {y_span:.3f} um (Expected: {expected_height} um)")

    assert round(x_span, 3) == expected_length, f"X span mismatch: {x_span} != {expected_length}"
    assert round(y_span, 3) == expected_height, f"Y span mismatch: {y_span} != {expected_height}"
    print("Footprint validation successful!")