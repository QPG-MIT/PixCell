import gdsfactory as gf
from gdsfactory.typings import ComponentSpec, CrossSectionSpec

# Define a custom component for the waveguide segment with teeth
@gf.cell
def teeth_segment(
    length: float,
    width_main_arm: float,
    teeth_width: float,
    teeth_spacing: float,
    teeth_height: float,
    layer: tuple,
    cross_section: CrossSectionSpec,
) -> gf.Component:
    """
    Creates a straight waveguide segment with teeth along one side (extending downwards).
    """
    c = gf.Component(f"teeth_segment_{length:.2f}")

    # Base straight waveguide
    base_straight = c << gf.components.straight(length=length, cross_section=cross_section)

    # Calculate number of teeth
    # Ensure length is sufficient for at least one tooth
    if length < teeth_width:
        num_teeth = 0
    else:
        num_teeth = int(length / (teeth_width + teeth_spacing))
    
    # Add teeth as rectangles
    for i in range(num_teeth):
        tooth_rect = c << gf.components.rectangle(
            size=(teeth_width, teeth_height), layer=layer, centered=False
        )
        # Position tooth: its top-left corner aligns with the bottom-left of the current tooth position
        # on the base_straight waveguide. The teeth extend downwards from the waveguide's bottom edge.
        tooth_rect.xmin = base_straight.xmin + i * (teeth_width + teeth_spacing)
        tooth_rect.ymax = base_straight.ymin  # Align top of tooth with bottom of waveguide

    # Expose ports for connecting this segment
    c.add_port("o1", port=base_straight.ports["o1"])
    c.add_port("o2", port=base_straight.ports["o2"])
    return c


@gf.cell
def custom_device(
    width_main_arm: float = 0.1,
    width_center_line: float = 0.1,
    total_length: float = 18.24,
    total_height: float = 0.7,
    taper_length: float = 2.0,
    bend_radius: float = 2.0,
    teeth_length: float = 8.0,
    teeth_width: float = 0.05,
    teeth_spacing: float = 0.1,
    teeth_height: float = 0.1,
    layer: tuple = (1, 0),
) -> gf.Component:
    """
    Recreates the given device geometry using GDSFactory parametric functions.
    """
    c = gf.Component("custom_device")

    # Define main cross-sections for the different elements
    # Pass radius=bend_radius to the cross_section to set its minimum bend radius
    xs_main_arm = gf.cross_section.cross_section(width=width_main_arm, layer=layer, radius=bend_radius)
    xs_center_line = gf.cross_section.cross_section(width=width_center_line, layer=layer)

    # 1. Calculate vertical gap and positions based on total_height constraint
    # total_height = 2 * width_main_arm + 2 * gap_vertical + width_center_line
    gap_vertical = (total_height - 2 * width_main_arm - width_center_line) / 2
    
    if gap_vertical < 0:
        raise ValueError(
            f"Total height {total_height} is too small for given widths: "
            f"2*{width_main_arm} (arms) + {width_center_line} (center) = {2*width_main_arm + width_center_line} um. "
            "Increase total_height or decrease arm/center_line widths."
        )

    # Center the entire device at y=0. Calculate y-center for each element.
    y_center_line_pos = 0
    y_top_arm_pos = y_center_line_pos + width_center_line / 2 + gap_vertical + width_main_arm / 2
    y_bottom_arm_pos = y_center_line_pos - (width_center_line / 2 + gap_vertical + width_main_arm / 2)

    # 2. Add Central Straight Line
    center_line_ref = c << gf.components.straight(length=total_length, cross_section=xs_center_line)
    center_line_ref.center = (total_length / 2, y_center_line_pos)

    # 3. Build the Upper Arm
    # Calculate horizontal segment lengths for the components between tapers and bends
    min_horizontal_length_for_bends_tapers = 2 * taper_length + 2 * bend_radius
    if total_length < min_horizontal_length_for_bends_tapers:
        raise ValueError(
            f"Total length {total_length} is too short for tapers and bends: "
            f"2 * {taper_length} (tapers) + 2 * {bend_radius} (bends) = {min_horizontal_length_for_bends_tapers:.2f} um. "
            "Increase total_length or decrease taper_length/bend_radius."
        )

    L_horizontal_mid = total_length - min_horizontal_length_for_bends_tapers
    
    if teeth_length > L_horizontal_mid:
        raise ValueError(
            f"Teeth length {teeth_length} is too long for the available horizontal segment "
            f"{L_horizontal_mid:.2f} um. Make teeth_length smaller."
        )
    
    L_straight_plain = (L_horizontal_mid - teeth_length) / 2
    if L_straight_plain < 0:
        L_straight_plain = 0  # Should not happen with prior checks, but as a safeguard.

    # Create a temporary component to assemble the top arm's elements
    top_arm_assembly = gf.Component("top_arm_assembly")

    # Left taper (starts with width 0, ends with width_main_arm)
    tl_ref = top_arm_assembly << gf.components.taper(length=taper_length, width1=0, width2=width_main_arm, cross_section=xs_main_arm)
    
    # Left Euler bend (curves down and right for top arm, so angle -90)
    bl_ref = top_arm_assembly << gf.components.bend_euler(radius=bend_radius, angle=-90, cross_section=xs_main_arm)
    bl_ref.connect("o1", tl_ref.ports["o2"])

    # Plain straight segment before teeth
    psl_ref = top_arm_assembly << gf.components.straight(length=L_straight_plain, cross_section=xs_main_arm)
    psl_ref.connect("o1", bl_ref.ports["o2"])

    # Teeth segment
    ts_ref = top_arm_assembly << teeth_segment(
        length=teeth_length,
        width_main_arm=width_main_arm,
        teeth_width=teeth_width,
        teeth_spacing=teeth_spacing,
        teeth_height=teeth_height,
        layer=layer,
        cross_section=xs_main_arm,
    )
    ts_ref.connect("o1", psl_ref.ports["o2"])

    # Plain straight segment after teeth
    psr_ref = top_arm_assembly << gf.components.straight(length=L_straight_plain, cross_section=xs_main_arm)
    psr_ref.connect("o1", ts_ref.ports["o2"])

    # Right Euler bend (curves up and left for top arm, so angle 90)
    br_ref = top_arm_assembly << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs_main_arm)
    br_ref.connect("o1", psr_ref.ports["o2"])

    # Right taper (starts with width_main_arm, ends with width 0)
    tr_ref = top_arm_assembly << gf.components.taper(length=taper_length, width1=width_main_arm, width2=0, cross_section=xs_main_arm)
    tr_ref.connect("o1", br_ref.ports["o2"])

    # Add the fully assembled top arm to the main component `c`
    top_arm_final_ref = c << top_arm_assembly
    # Position the entire top arm: The `top_arm_assembly` was built with its first component (taper)
    # starting at local y=0. We want its centerline to be at `y_top_arm_pos`.
    top_arm_final_ref.y = y_top_arm_pos

    # 4. Create the Lower Arm by mirroring the Upper Arm
    # Mirroring across the x-axis (y=0) will invert its y-coordinates.
    # The `top_arm_assembly.mirror((0,0), (1,0))` creates a new component with all its elements mirrored.
    bottom_arm_assembly_mirrored = top_arm_assembly.mirror((0, 0), (1, 0))
    bottom_arm_final_ref = c << bottom_arm_assembly_mirrored
    
    # Position the mirrored bottom arm. Its local y-center will now be at `-y_top_arm_pos`.
    # We need to explicitly set its y-position to `y_bottom_arm_pos` to match the calculated symmetric position.
    bottom_arm_final_ref.y = y_bottom_arm_pos

    return c


if __name__ == "__main__":
    # Create the device with default parameters
    device = custom_device()
    
    # Verify the footprint matches the constraint
    # FIX: Use .bbox attribute instead of .bbox_ps() method
    bbox = device.bbox 
    width_actual = bbox[1][0] - bbox[0][0]
    height_actual = bbox[1][1] - bbox[0][1]

    print(f"Actual device width: {width_actual:.2f} um (Expected: 18.24 um)")
    print(f"Actual device height: {height_actual:.2f} um (Expected: 0.70 um)")

    # You can visualize the device using gf.show() or save it to a GDS file
    # gf.show(device)
    device.write_gds("custom_device.gds")

    # Example of how to inspect a sub-component (e.g., the teeth segment)
    # teeth_comp = teeth_segment(length=8.0, width_main_arm=0.1, teeth_width=0.05,
    #                            teeth_spacing=0.1, teeth_height=0.1, layer=(1,0),
    #                            cross_section=gf.cross_section.cross_section(width=0.1, layer=(1,0)))
    # gf.show(teeth_comp)