import gdsfactory as gf
import numpy as np

@gf.cell
def custom_device_from_image():
    """
    Recreates the geometry from the provided image using GDSFactory parametric functions.

    The device consists of a central straight waveguide and two symmetric top/bottom
    arms that start narrow, flare outwards and inwards with angular transitions,
    and also vary in width along their path.
    """
    c = gf.Component("device_from_image_angular")

    # Define a common layer for all structures
    LAYER = (1, 0)

    # --- Device Footprint Constraints ---
    L_TOTAL = 40.0 # micrometers, total length of the device
    H_TOTAL = 1.7  # micrometers, total height of the device

    # --- Parameters for the Central Waveguide ---
    w_center = 0.1 # Width of the central straight waveguide
    l_center = 20.0 # Length of the central straight waveguide
    
    xs_center = gf.cross_section.cross_section(width=w_center, layer=LAYER)
    center_wg = c << gf.components.straight(length=l_center, cross_section=xs_center)
    center_wg.xmin = 0
    center_wg.y = 0

    # --- Parameters for the Top and Bottom Arms ---
    w_arm_init = 0.2  # Initial (narrow) width of the arms
    w_arm_max = 0.4   # Maximum (wider) width of the arms

    # --- Helper function for creating the varying width CrossSection ---
    def create_varying_width_cross_section(path_points, widths_at_points, layer):
        """
        Creates a CrossSection with a width attribute that is a callable function.
        This function interpolates widths_at_points based on the path_points
        along the normalized path length 't'.
        """
        # Calculate cumulative lengths of the path segments
        path_segments_lengths = []
        for i in range(len(path_points) - 1):
            segment_length = np.linalg.norm(np.array(path_points[i+1]) - np.array(path_points[i]))
            path_segments_lengths.append(segment_length)
        
        cumulative_lengths = np.cumsum([0.0] + path_segments_lengths)
        total_path_length = cumulative_lengths[-1]

        def width_function(t):
            """
            Returns the interpolated width at a given normalized path position 't'.
            """
            if total_path_length == 0: # Handle paths with no length (e.g., single point)
                return widths_at_points[0] if widths_at_points else 0.5
            
            # Convert normalized 't' (0 to 1) to actual length along the path
            current_length = t * total_path_length

            # Find the segment where 'current_length' falls
            for i in range(len(cumulative_lengths) - 1):
                if cumulative_lengths[i] <= current_length <= cumulative_lengths[i+1]:
                    segment_start_length = cumulative_lengths[i]
                    segment_end_length = cumulative_lengths[i+1]
                    width_start = widths_at_points[i]
                    width_end = widths_at_points[i+1]

                    if segment_end_length == segment_start_length:
                        # Zero-length segment (e.g., repeated points), return start width
                        return width_start
                    
                    # Linear interpolation factor within the segment
                    alpha = (current_length - segment_start_length) / (segment_end_length - segment_start_length)
                    return (1 - alpha) * width_start + alpha * width_end
            
            # Handle boundary conditions in case of floating point inaccuracies
            if t <= 0: return widths_at_points[0]
            if t >= 1: return widths_at_points[-1]
            return widths_at_points[0] # Fallback, should ideally not be reached

        # --- FIX APPLIED HERE ---
        # Use gf.cross_section.cross_section to create the CrossSection with a callable width
        return gf.cross_section.cross_section(width=width_function, layer=layer)


    # --- Top Arm Construction ---
    points_top_arm_cl = [
        (0, 0.25),      # P0: Start point
        (8, 0.25),      # P1: End of initial narrow straight section
        (15, 0.55),     # P2: First sharp outward angle
        (20, 0.65),     # P3: Peak outward Y for the centerline
        (25, 0.35),     # P4: Sharp inward angle
        (30, 0.45),     # P5: Second sharp outward angle
        (35, 0.45),     # P6: Start of final wider straight section
        (L_TOTAL, 0.45) # P7: End of the arm
    ]
    widths_top_arm = [
        w_arm_init, # Width at P0
        w_arm_init, # Width at P1
        0.3,        # Width at P2
        w_arm_max,  # Width at P3
        0.25,       # Width at P4
        w_arm_max,  # Width at P5
        w_arm_max,  # Width at P6
        w_arm_max   # Width at P7
    ]

    path_top = gf.Path(points_top_arm_cl)
    # Create the custom CrossSection for the top arm's varying width
    xs_varying_top = create_varying_width_cross_section(points_top_arm_cl, widths_top_arm, LAYER)
    # Extrude the path using the custom CrossSection
    arm_top = c << gf.path.extrude(path_top, xs_varying_top)

    # --- Bottom Arm Construction (Mirrored from Top Arm) ---
    points_bottom_arm_cl = [(p[0], -p[1]) for p in points_top_arm_cl]
    widths_bottom_arm = widths_top_arm # Same widths for symmetric arm

    path_bottom = gf.Path(points_bottom_arm_cl)
    # Create the custom CrossSection for the bottom arm
    xs_varying_bottom = create_varying_width_cross_section(points_bottom_arm_cl, widths_bottom_arm, LAYER)
    # Extrude the path using the custom CrossSection
    arm_bottom = c << gf.path.extrude(path_bottom, xs_varying_bottom)

    return c

if __name__ == "__main__":
    # Create the device
    device = custom_device_from_image()

    # Write the GDSII file
    device.write_gds("device_from_image_angular.gds")

    # To visualize the device (requires KLayout or similar viewer configured with gdsfactory)
    # device.show()