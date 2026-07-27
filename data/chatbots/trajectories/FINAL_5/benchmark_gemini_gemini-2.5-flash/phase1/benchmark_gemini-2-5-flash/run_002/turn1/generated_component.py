import gdsfactory as gf
import numpy as np

@gf.cell
def tooth_segment(length, num_solid_segments, solid_width, gap_width_val, cross_section):
    """Creates a straight waveguide with periodic gaps (teeth).
    This function is defined but not directly used in custom_device below,
    as the tooth holes are created explicitly for boolean operations to integrate
    with the path-based geometry."""
    c = gf.Component("toothed_waveguide")
    
    # Create the base straight waveguide as a rectangle
    base_straight = gf.components.rectangle(
        size=(length, cross_section.width), 
        layer=cross_section.layer, 
        centered=True
    )
    
    # Create a temporary component for the gaps
    gaps_comp = gf.Component("gaps_for_subtraction")
    
    # Calculate total length of the toothed pattern
    pattern_length = num_solid_segments * solid_width + (num_solid_segments - 1) * gap_width_val
    
    # Calculate x-coordinate of the center of the first gap, relative to the center of the base_straight
    first_gap_center_x = -length / 2 + (length - pattern_length) / 2 + solid_width + gap_width_val / 2
    
    for i in range(num_solid_segments - 1):
        gap_rect = gaps_comp << gf.components.rectangle(
            size=(gap_width_val, cross_section.width), 
            layer=cross_section.layer, 
            centered=True
        )
        gap_rect.x = first_gap_center_x + i * (solid_width + gap_width_val)
    
    # Perform boolean subtraction
    result = gf.boolean(
        A=base_straight,
        B=gaps_comp,
        operation="not",
        layer=cross_section.layer
    )
    c.add_ref(result)
    
    # Add ports to the component (optional, but good practice if it's part of a larger netlist)
    c.add_port("o1", center=(-length/2, 0), width=cross_section.width, orientation=180, layer=cross_section.layer)
    c.add_port("o2", center=(length/2, 0), width=cross_section.width, orientation=0, layer=cross_section.layer)
    return c


@gf.cell
def custom_device():
    c = gf.Component("custom_device")

    # Dimensions from constraint
    total_width = 18.24
    total_height = 0.7

    # Derived parameters
    line_width = 0.05
    gap_center_tooth = 0.05 # Gap between central line and toothed lines
    
    # Y-level for center of toothed lines (top/bottom)
    y_center_tooth = line_width / 2 + gap_center_tooth + line_width / 2 # = 0.025 + 0.05 + 0.025 = 0.1 um
    
    # Cross-section definition
    xs = gf.cross_section.cross_section(width=line_width, layer=(1, 0))

    # 1. Central Straight Waveguide
    central_wg = c << gf.components.straight(length=total_width, cross_section=xs)
    central_wg.center = (0, 0) # Center the central waveguide

    # 2. Toothed Segment Parameters
    tooth_segment_length = 12.0 # Total length of the straight section for teeth in the path
    num_solid_segments = 28
    solid_width = 0.2
    gap_width_val = 0.2
    
    # Horn and Taper Parameters
    L_taper = 1.0 # Length of the final pointed taper
    
    # R_euler_bend must achieve vertical displacement of (total_height/2 - y_center_tooth) = 0.35 - 0.1 = 0.25
    # For two 90-degree Euler bends in an S-curve, total vertical displacement = 2 * R_euler_bend
    R_euler_bend = (total_height/2 - y_center_tooth) / 2 # = 0.25 / 2 = 0.125 um
    
    L_horn_straight_start = 0.7 # horizontal straight before first bend (outermost)
    L_horn_straight_end = 0.7 # horizontal straight after second bend (connecting to tooth section)

    # Calculate L_horn_straight_middle to fit total_width
    # Target horizontal span for the extruded path (excluding the L_taper sections)
    target_path_horizontal_span = total_width - 2 * L_taper # 18.24 - 2*1.0 = 16.24
    
    # Each 90-degree Euler bend contributes R_euler_bend to horizontal span
    dx_euler_90 = R_euler_bend 

    # Total horizontal span of the path is:
    # 2 * (L_horn_straight_start + dx_euler_90 + L_horn_straight_middle + dx_euler_90 + L_horn_straight_end) + tooth_segment_length
    # Solving for L_horn_straight_middle:
    L_horn_straight_middle = (
        target_path_horizontal_span 
        - (2 * (L_horn_straight_start + L_horn_straight_end + 2 * dx_euler_90) + tooth_segment_length)
    ) / 2.0
    
    if L_horn_straight_middle < 0.05: # Ensure it's not too small or negative
        print(f"Warning: L_horn_straight_middle calculated as {L_horn_straight_middle:.3f}. Clamping to 0.05.")
        L_horn_straight_middle = 0.05

    # --- TOP ARM CONSTRUCTION ---
    # Create the path for the top arm's centerline
    p_top_arm = gf.Path()
    
    # Left S-bend (horn) part
    p_top_arm.append(gf.path.straight(length=L_horn_straight_start)) # Initial horizontal straight
    p_top_arm.append(gf.path.euler(radius=R_euler_bend, angle=-90)) # Curve down-right
    p_top_arm.append(gf.path.straight(length=L_horn_straight_middle)) # Horizontal straight between bends
    p_top_arm.append(gf.path.euler(radius=R_euler_bend, angle=-90)) # Curve further down-right
    p_top_arm.append(gf.path.straight(length=L_horn_straight_end)) # Final straight before tooth section

    # Middle straight section (where teeth will be)
    p_top_arm.append(gf.path.straight(length=tooth_segment_length))

    # Right S-bend (horn) part (mirrored logic of left horn)
    p_top_arm.append(gf.path.straight(length=L_horn_straight_end))
    p_top_arm.append(gf.path.euler(radius=R_euler_bend, angle=90)) # Curve up-right
    p_top_arm.append(gf.path.straight(length=L_horn_straight_middle))
    p_top_arm.append(gf.path.euler(radius=R_euler_bend, angle=90)) # Curve further up-right
    p_top_arm.append(gf.path.straight(length=L_horn_straight_start)) # Final horizontal straight

    # Extrude the path to create the constant-width top arm component
    top_arm_extruded = gf.path.extrude(p_top_arm, cross_section=xs)
    top_arm_ref = c << top_arm_extruded
    
    # Position the top arm:
    # The path starts at y=0, then dips to -2*R_euler_bend, then comes back to y=0.
    # So the path's highest Y (relative to its start) is 0.
    # To place its highest Y at total_height/2:
    top_arm_ref.y = total_height/2 

    # Calculate the total horizontal length of the path (component's x-span)
    path_actual_x_span = (
        2 * (L_horn_straight_start + L_horn_straight_middle + L_horn_straight_end + 2 * R_euler_bend)
        + tooth_segment_length
    )
    # Center the component horizontally.
    # `extrude` typically places the start of the path at the component's (0,0).
    # To center the *entire geometry*, shift it by half its X-span to the left.
    top_arm_ref.x = -path_actual_x_span / 2 

    # --- Boolean Operations for Tapers and Teeth ---
    # Create a single component to hold all geometries for subtraction
    subtractions_comp = gf.Component("subtractions")
    
    # 1. Create the tooth gaps (rectangles)
    tooth_holes_comp = gf.Component("tooth_holes_for_top_arm")
    
    pattern_length = num_solid_segments * solid_width + (num_solid_segments - 1) * gap_width_val
    
    # Calculate the x-offset for the tooth pattern, centered within tooth_segment_length
    x_start_pattern_within_segment = -tooth_segment_length / 2 + (tooth_segment_length - pattern_length) / 2
    
    for i in range(num_solid_segments - 1):
        gap_x = x_start_pattern_within_segment + solid_width + gap_width_val / 2 + i * (solid_width + gap_width_val)
        
        gap_rect = gf.components.rectangle(
            size=(gap_width_val, xs.width),
            layer=xs.layer,
            centered=True
        )
        gap_rect_ref = tooth_holes_comp << gap_rect
        gap_rect_ref.x = gap_x # X-position relative to center of `tooth_segment_length`
        gap_rect_ref.y = y_center_tooth # The Y-level where the tooth pattern resides for the top arm
    
    subtractions_comp.add_ref(tooth_holes_comp) # Add the tooth holes to the subtraction component

    # 2. Create and add taper shapes (triangles) for subtraction
    
    # Left Taper
    taper_left_end_x = -total_width/2 # Global x-coord of the tip
    taper_left_start_x = taper_left_end_x + L_taper # Global x-coord where taper starts (constant width)
    taper_y_min = top_arm_ref.y - xs.width/2 # Bottom edge of the top arm at taper start
    taper_y_max = top_arm_ref.y + xs.width/2 # Top edge of the top arm at taper start
    
    subtractions_comp.add_polygon(
        points=[
            (taper_left_start_x, taper_y_max),
            (taper_left_start_x, taper_y_min),
            (taper_left_end_x, top_arm_ref.y) # Pointed tip
        ],
        layer=xs.layer
    )
    
    # Right Taper
    taper_right_end_x = total_width/2
    taper_right_start_x = taper_right_end_x - L_taper
    
    subtractions_comp.add_polygon(
        points=[
            (taper_right_start_x, taper_y_min),
            (taper_right_start_x, taper_y_max),
            (taper_right_end_x, top_arm_ref.y)
        ],
        layer=xs.layer
    )
    
    # Final boolean operation for the top arm: subtract all holes and tapers
    final_top_arm = gf.boolean(
        A=top_arm_ref, # The extruded path
        B=subtractions_comp,
        operation="not",
        layer=xs.layer
    )
    c.add_ref(final_top_arm)

    # --- BOTTOM ARM CONSTRUCTION ---
    # Create the bottom arm by mirroring the final top arm
    bottom_arm_ref = c << final_top_arm
    bottom_arm_ref.mirror(p1=(0,0), p2=(1,0)) # Mirror across X-axis (y=0)
    
    return c

if __name__ == "__main__":
    # Create the device
    c = custom_device()
    c.write_gds("custom_device.gds")
    
    # Verify footprint
    bbox = c.bbox
    actual_width = bbox[1][0] - bbox[0][0]
    actual_height = bbox[1][1] - bbox[0][1]
    
    print(f"Designed device footprint: W={actual_width:.2f}um, H={actual_height:.2f}um")
    # Expected: W=18.24um, H=0.70um