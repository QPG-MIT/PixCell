import gdsfactory as gf

@gf.cell
def crossover_waveguides() -> gf.Component:
    """
    Recreates the geometry from the provided image showing two waveguides
    smoothly crossing over each other, using GDSFactory parametric functions.
    """
    c = gf.Component("crossover_waveguides")

    # Define the waveguide cross-section
    # Assuming a standard width of 0.5 um on layer (1, 0)
    xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))

    # --- Derived Parameters from Footprint [120, 4] um ---
    # These are specific to this component's design based on the problem's footprint.
    total_length = 120  # Total horizontal length of the device
    total_height = 4    # Total vertical height of the device

    # Calculate the centerline Y-coordinate for the outermost part of the waveguides.
    # Total height / 2 = 2.0 (half height of footprint)
    # Waveguide width / 2 = 0.25 (half width of the waveguide)
    # y_outer_centerline = (total_height / 2) - (xs.width / 2) = 2.0 - 0.25 = 1.75 um
    y_outer_centerline = (total_height / 2) - (xs.width / 2) # 1.75 um

    # The total vertical displacement for each waveguide to cross over.
    # From +y_outer_centerline to -y_outer_centerline (or vice versa).
    # dy_crossover = y_outer_centerline - (-y_outer_centerline) = 2 * y_outer_centerline = 3.5 um
    dy_crossover = 2 * y_outer_centerline # 3.5 um

    # The horizontal length for each S-bend, which spans the entire device.
    dx_crossover = total_length # 120 um

    # 1. Create the top-left to bottom-right crossover waveguide.
    # This waveguide starts high (+y) and ends low (-y), so dy is negative.
    crossover_top_to_bottom = c << gf.components.bend_s(
        size=(dx_crossover, -dy_crossover), cross_section=xs
    )
    # Position its 'o1' port at the far left (x = -total_length/2),
    # at the initial top-left Y position (+y_outer_centerline).
    crossover_top_to_bottom.movex(-total_length / 2)
    crossover_top_to_bottom.movey(y_outer_centerline)

    # 2. Create the bottom-left to top-right crossover waveguide.
    # This waveguide starts low (-y) and ends high (+y), so dy is positive.
    crossover_bottom_to_top = c << gf.components.bend_s(
        size=(dx_crossover, dy_crossover), cross_section=xs
    )
    # Position its 'o1' port at the far left (x = -total_length/2),
    # at the initial bottom-left Y position (-y_outer_centerline).
    crossover_bottom_to_top.movex(-total_length / 2)
    crossover_bottom_to_top.movey(-y_outer_centerline)

    # 3. Add external ports to the main component for device interface.
    # Input ports on the left:
    c.add_port("o1_top", port=crossover_top_to_bottom.ports["o1"])
    c.add_port("o1_bottom", port=crossover_bottom_to_top.ports["o1"])

    # Output ports on the right:
    # The waveguide starting at 'o1_top' ends at the bottom-right.
    c.add_port("o2_bottom", port=crossover_top_to_bottom.ports["o2"])
    # The waveguide starting at 'o1_bottom' ends at the top-right.
    c.add_port("o2_top", port=crossover_bottom_to_top.ports["o2"])

    return c

if __name__ == "__main__":
    # Create the device component
    device = crossover_waveguides()

    # Write the GDS file for the device
    device.write_gds("crossover_device.gds")

    # Optional: Display the component in KLayout or other GDS viewer
    # device.show()

    # Validate footprint (optional, for verification)
    bbox = device.bbox()
    # Corrected access to DBox attributes: use .left, .right, .bottom, .top
    x_span = bbox.right - bbox.left
    y_span = bbox.top - bbox.bottom

    # Define the expected footprint values here for comparison,
    # as they are given in the problem statement.
    expected_length = 120
    expected_height = 4

    print(f"Calculated X span: {x_span} um (Expected: {expected_length} um)")
    print(f"Calculated Y span: {y_span} um (Expected: {expected_height} um)")