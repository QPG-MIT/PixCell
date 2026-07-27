import gdsfactory as gf
import numpy as np

@gf.cell
def custom_device_from_image_v2_fixed():
    """
    Recreates the geometry from the provided image (kinked outer prongs,
    blunt central prong) using GDSFactory parametric functions.
    Fixes the CrossSection width validation error by decomposing the outer arms
    into connected gf.components.straight and gf.components.taper segments.
    """
    c = gf.Component("device_from_image_v2_fixed")

    LAYER = (1, 0) # Define the layer for the geometry
    
    # --- Parameters derived from image analysis and footprint (40.0 x 1.7 um) ---

    # Input prong dimensions
    width_prong = 0.25  # Width of each of the three input waveguides
    gap_between_prongs = 0.475  # Gap between the input waveguides

    # Y-coordinates for the centerlines of the input prongs (assuming overall structure centered at Y=0)
    y_middle_center = 0
    y_top_center = y_middle_center + width_prong / 2 + gap_between_prongs + width_prong / 2  # 0.725 um
    y_bottom_center = y_middle_center - (width_prong / 2 + gap_between_prongs + width_prong / 2) # -0.725 um

    # Overall length parameter
    L_total = 40.0

    # --- 1. Create the Central Prong (Straight waveguide with blunt end) ---
    x_center_end_blunt = 20.0 # Horizontal position where the central prong ends

    central_prong_comp = gf.components.straight(
        length=x_center_end_blunt,
        cross_section=gf.cross_section.cross_section(width=width_prong, layer=LAYER)
    )

    # --- 2. Create the Top Merging Arm using connected straight and taper segments ---
    # Define path points for the centerline of the top arm
    path_points_top_arm = [
        (0, y_top_center),
        (10.0, y_top_center),
        (25.0, 0.55),       # First kink point, y-coordinate for centerline
        (30.0, 0.425),      # Second kink point, y-coordinate for centerline
        (L_total, 0.425)    # End point for centerline
    ]
    # Define corresponding widths at each path point
    widths_at_path_points = [
        width_prong,  # At (0, y_top_center)
        width_prong,  # At (10.0, y_top_center)
        0.50,         # At (25.0, 0.55) - wider
        0.65,         # At (30.0, 0.425) - even wider
        0.65          # At (40.0, 0.425) - maintains width
    ]

    # Component to hold the assembled segments of the top arm
    top_arm_segments = gf.Component("top_arm_segments")
    current_port = None # To keep track of the last segment's output port

    for i in range(len(path_points_top_arm) - 1):
        p_start = path_points_top_arm[i]
        p_end = path_points_top_arm[i+1]
        w_start = widths_at_path_points[i]
        w_end = widths_at_path_points[i+1]

        dx = p_end[0] - p_start[0]
        dy = p_end[1] - p_start[1]
        segment_length = np.sqrt(dx**2 + dy**2)
        segment_angle_deg = np.degrees(np.arctan2(dy, dx))

        # Create either a straight or a taper component
        if np.isclose(w_start, w_end): # It's a straight segment
            segment_comp = gf.components.straight(
                length=segment_length,
                cross_section=gf.cross_section.cross_section(width=w_start, layer=LAYER)
            )
        else: # It's a tapered segment
            segment_comp = gf.components.taper(
                length=segment_length,
                width1=w_start,
                width2=w_end,
                # For taper, the cross_section mainly provides the layer. width1/width2 define the taper.
                cross_section=gf.cross_section.cross_section(width=w_start, layer=LAYER) 
            )

        ref = top_arm_segments << segment_comp
        
        if current_port is None:
            # First segment: rotate and move to the initial start point
            ref.rotate(segment_angle_deg)
            # The 'o1' port of a straight/taper is at its start. Move its start to p_start.
            ref.move(origin=ref.ports["o1"], destination=p_start)
        else:
            # Connect subsequent segments' 'o1' port to the previous segment's 'o2' port
            ref.connect("o1", current_port)
        
        current_port = ref.ports["o2"] # Update current_port for the next iteration

    top_arm_comp = top_arm_segments # Assign the assembled component

    # --- 3. Create the Bottom Merging Arm (Mirrored segments of the top arm) ---
    bottom_arm_segments = gf.Component("bottom_arm_segments")
    current_port_bottom = None

    # Mirroring path points for the bottom arm (y-coordinates become negative)
    path_points_bottom_arm = [ (p[0], -p[1]) for p in path_points_top_arm ]

    for i in range(len(path_points_bottom_arm) - 1):
        p_start = path_points_bottom_arm[i]
        p_end = path_points_bottom_arm[i+1]
        w_start = widths_at_path_points[i]
        w_end = widths_at_path_points[i+1]

        dx = p_end[0] - p_start[0]
        dy = p_end[1] - p_start[1]
        segment_length = np.sqrt(dx**2 + dy**2)
        segment_angle_deg = np.degrees(np.arctan2(dy, dx))

        if np.isclose(w_start, w_end): # Straight segment
            segment_comp = gf.components.straight(
                length=segment_length,
                cross_section=gf.cross_section.cross_section(width=w_start, layer=LAYER)
            )
        else: # Tapered segment
            segment_comp = gf.components.taper(
                length=segment_length,
                width1=w_start,
                width2=w_end,
                cross_section=gf.cross_section.cross_section(width=w_start, layer=LAYER)
            )

        ref = bottom_arm_segments << segment_comp
        
        if current_port_bottom is None:
            ref.rotate(segment_angle_deg)
            ref.move(origin=ref.ports["o1"], destination=p_start)
        else:
            ref.connect("o1", current_port_bottom)
        
        current_port_bottom = ref.ports["o2"]

    bottom_arm_comp = bottom_arm_segments # Assign the assembled component


    # --- 4. Final Assembly: Boolean operations ---
    # Combine the top and bottom arms using a boolean OR operation
    c_outer_merged = gf.boolean(top_arm_comp, bottom_arm_comp, operation="or", layer=LAYER)

    # Combine the outer structure with the central prong using boolean OR
    final_device_geom = gf.boolean(c_outer_merged, central_prong_comp, operation="or", layer=LAYER)
    
    # Add the final device geometry to the main component
    c << final_device_geom

    return c

# --- Example Usage ---
if __name__ == "__main__":
    device = custom_device_from_image_v2_fixed()
    device.write_gds("custom_device_from_image_v2_fixed.gds")
    # For visualization, if KLayout is configured (e.g., gf.set_visual_editor("klayout"))
    # device.show()
    print(f"Device created: {device.name}.gds")
    print(f"Device bounding box: {device.bbox}") # Check against [40.0, 1.7]

    # Assertions to ensure footprint constraints are met
    L_total = 40.0
    assert np.isclose(device.bbox[0], 0.0) and np.isclose(device.bbox[2], L_total), f"X extent mismatch! Expected [0, {L_total}], got {device.bbox[[0,2]]}"
    assert np.isclose(device.bbox[1], -0.85, atol=1e-3) and np.isclose(device.bbox[3], 0.85, atol=1e-3), f"Y extent mismatch! Expected [-0.85, 0.85], got {device.bbox[[1,3]]}"