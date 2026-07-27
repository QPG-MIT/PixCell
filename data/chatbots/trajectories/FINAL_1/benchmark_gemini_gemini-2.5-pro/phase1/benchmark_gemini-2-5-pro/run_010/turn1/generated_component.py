import gdsfactory as gf

@gf.cell
def create_device():
    """Creates the trident-fork device."""

    # 1. Define parameters based on footprint and visual analysis
    total_length = 40.0
    total_height = 1.7

    # Divide the device into a straight section and a curved section
    straight_length = 25.0
    bend_length = total_length - straight_length

    # Define widths and gaps to achieve the outward curve and final height
    w_center_start = 0.4   # Start width of the central taper
    w_center_end = 0.1     # End width (tip) of the central taper
    w_outer_start = 0.4    # Start width of the outer arms
    w_outer_mid = 0.2      # Minimum width of outer arms (at the bend start)
    w_outer_end = 0.5      # Final width of the outer arms
    gap_start = 0.1        # Initial gap between central and outer elements

    # 2. Calculate y-positions for the centerlines of the outer arms
    # Initial y-position at x=0
    y_start_outer = (w_center_start / 2) + gap_start + (w_outer_start / 2)
    # Final y-position at x=total_length
    y_end_outer = (total_height - w_outer_end) / 2
    # Vertical displacement for the bend
    dy = y_end_outer - y_start_outer

    # 3. Create the composite outer arm component in a separate cell
    @gf.cell
    def trident_arm():
        """Creates one of the outer arms."""
        c = gf.Component()

        # Part A: Straight tapering section
        taper_straight = gf.components.taper(
            length=straight_length, width1=w_outer_start, width2=w_outer_mid
        )

        # Part B: Curved, widening section using bend_s with a transition
        
        # Define the tapering cross-section as a hashable dictionary.
        # This is the standard way to pass complex cross-sections to cached components.
        tapering_cross_section_spec = {
            "function": "transition",
            "cross_section1": {"function": "cross_section", "settings": {"width": w_outer_mid}},
            "cross_section2": {"function": "cross_section", "settings": {"width": w_outer_end}},
        }

        # Create the S-bend component using the dictionary spec for its cross-section.
        taper_bend = gf.components.bend_s(
            size=(bend_length, dy), cross_section=tapering_cross_section_spec
        )

        # Assemble the two parts of the arm
        ref_straight = c << taper_straight
        ref_bend = c << taper_bend
        ref_bend.connect("o1", ref_straight.ports["o2"])

        # Add ports to the composite arm
        c.add_port("o1", port=ref_straight.ports["o1"])
        c.add_port("o2", port=ref_bend.ports["o2"])
        return c

    # 4. Assemble the final device
    c = gf.Component("trident_splitter")

    # Add the central taper
    center_taper = gf.components.taper(
        length=straight_length, width1=w_center_start, width2=w_center_end
    )
    c.add_ref(center_taper)

    # Instantiate the arm component
    arm = trident_arm()

    # Add and position the top arm
    arm_top_ref = c << arm
    arm_top_ref.movey(y_start_outer)

    # Add, mirror, and position the bottom arm
    arm_bottom_ref = c << arm
    arm_bottom_ref.mirror()
    arm_bottom_ref.movey(-y_start_outer)

    return c

# Instantiate the final component
device = create_device()