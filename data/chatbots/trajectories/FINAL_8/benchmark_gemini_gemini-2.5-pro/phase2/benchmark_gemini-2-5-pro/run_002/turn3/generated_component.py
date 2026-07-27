import gdsfactory as gf
import numpy as np

@gf.cell
def create_device():
    """
    Creates a symmetric device with a central straight section flanked by
    two smoothly curving outer arms.

    This function follows a structured, component-based approach:
    1.  Define geometric parameters (widths, gaps, lengths, radius) that
        are tuned to match the target image and footprint constraints.
    2.  Create a "top_arm" sub-component. This arm consists of a thick
        solid bar and six parallel thin lines, all following a path made
        from a horizontal straight, an Euler bend, and an angled straight.
    3.  Create a "center_lines" sub-component, which is a simple stack of
        five parallel straight waveguides.
    4.  Assemble the final device by instantiating the center lines, the top
        arm, and a mirrored version of the top arm for the bottom. These
        components are then aligned relative to each other's bounding boxes
        for a robust and precise final layout.
    """
    c = gf.Component("FinalDevice")

    # --- 1. Define Parameters & Cross Sections ---
    # These parameters are estimated to fit the aspect ratio and footprint
    line_width = 0.1
    gap = 0.1
    pitch = line_width + gap
    solid_width = 0.4
    main_gap = 0.15  # Gap between solid arm and central lines

    # Arm geometry
    bend_radius = 6.0
    bend_angle = -65.0
    length_angled_straight = 50.0
    length_horizontal_straight = 65.0
    
    # Central section geometry
    center_length = 65.0 # Match the horizontal arm length for a cleaner look

    # FIX: The `cross_section` factory does not accept `min_bend_radius`.
    # The correct procedure is to create a cross-section and then use
    # `gf.cross_section.copy()` to create a new version with the `radius_min`
    # attribute (the correct name) overridden.

    # Define base cross-sections
    xs_thin_base = gf.cross_section.cross_section(width=line_width, layer=(1, 0))
    xs_solid_base = gf.cross_section.cross_section(width=solid_width, layer=(1, 0))

    # Create copies with the desired minimum radius
    xs_thin = gf.cross_section.copy(xs_thin_base, radius_min=bend_radius)
    xs_solid = gf.cross_section.copy(xs_solid_base, radius_min=bend_radius)


    # --- 2. Create the Top Arm Sub-Component ---
    top_arm = gf.Component("TopArm")

    # Create and place the solid bar (the lowest element in the arm)
    s_h_solid = top_arm << gf.components.straight(length=length_horizontal_straight, cross_section=xs_solid)
    bend_solid = top_arm << gf.components.bend_euler(radius=bend_radius, angle=bend_angle, cross_section=xs_solid)
    s_a_solid = top_arm << gf.components.straight(length=length_angled_straight, cross_section=xs_solid)
    bend_solid.connect("o1", s_h_solid.ports["o2"])
    s_a_solid.connect("o1", bend_solid.ports["o2"])

    # Create and stack the 6 thin lines above the solid bar
    for i in range(6):
        s_h = top_arm << gf.components.straight(length=length_horizontal_straight, cross_section=xs_thin)
        bend = top_arm << gf.components.bend_euler(radius=bend_radius, angle=bend_angle, cross_section=xs_thin)
        s_a = top_arm << gf.components.straight(length=length_angled_straight, cross_section=xs_thin)
        
        # Connect the parts of the line
        bend.connect("o1", s_h.ports["o2"])
        s_a.connect("o1", bend.ports["o2"])

        # Calculate the vertical position for this line
        y_offset = (solid_width / 2) + gap + (line_width / 2) + (i * pitch)
        
        # Move all parts of the line up
        s_h.movey(y_offset)
        bend.movey(y_offset)
        s_a.movey(y_offset)

    # --- 3. Create the Central Lines Sub-Component ---
    center_lines = gf.Component("CenterLines")
    for i in range(5):
        wg = center_lines.add_ref(
            gf.components.straight(length=center_length, cross_section=xs_thin)
        )
        wg.movey(i * pitch)
    # Center the entire block of lines around y=0 for easy assembly
    center_lines.movey(-center_lines.size_info.center[1])


    # --- 4. Assemble the Final Device ---
    # Add all sub-components as references
    top_ref = c.add_ref(top_arm)
    bottom_ref = c.add_ref(top_arm)
    center_ref = c.add_ref(center_lines)

    # Mirror the bottom arm across the x-axis
    bottom_ref.mirror()

    # Align the components horizontally
    # The origin of the arm component is at the start of the horizontal straight.
    # The bend starts at x=length_horizontal_straight relative to that origin.
    # We move the arm so the bend starts at x=0 in the final component.
    top_ref.x = -length_horizontal_straight
    bottom_ref.x = -length_horizontal_straight
    
    # Align the right edge of the central lines to where the bends start (x=0).
    center_ref.xmax = 0

    # Align the components vertically
    # Position top arm above the central lines with the defined main_gap
    top_ref.y = center_ref.ymax + main_gap + solid_width / 2
    
    # Position bottom arm below the central lines
    bottom_ref.y = center_ref.ymin - main_gap - solid_width / 2
    
    # Center the entire device at (0,0)
    c.move(-c.size_info.center)

    return c


# Instantiate the cell to create the component
device = create_device()

# Save the component to a GDS file.
device.write_gds("output.gds")
print("GDS file saved as 'output.gds'")