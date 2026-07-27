import gdsfactory as gf

@gf.cell
def custom_device_from_image():
    """
    Recreates the geometry from the provided image using GDSFactory
    parametric functions and boolean operations.
    """
    c = gf.Component("device_from_image")

    # Define the layer for the geometry (assuming a single layer for black parts)
    LAYER = (1, 0)

    # --- Parameters derived from image analysis and footprint (40.0 x 1.7 um) ---

    # Input prong dimensions
    width_prong = 0.25  # Width of each of the three input waveguides
    gap_between_prongs = 0.475  # Gap between the input waveguides

    # Verify total height: 3 * 0.25 + 2 * 0.475 = 0.75 + 0.95 = 1.7 um (Matches footprint)

    # Output waveguide width
    width_output = 1.0  # Width of the combined output waveguide

    # Y-coordinates for the centerlines of the input prongs (assuming overall structure centered at Y=0)
    y_middle_center = 0
    y_top_center = y_middle_center + width_prong / 2 + gap_between_prongs + width_prong / 2  # 0.725 um
    y_bottom_center = y_middle_center - (width_prong / 2 + gap_between_prongs + width_prong / 2) # -0.725 um

    # Overall length parameters
    L_total = 40.0
    L_initial_straight_outer = 10.0  # Length of the initial straight part of outer arms
    L_curve_outer_dx = 15.0         # Horizontal extent of the curving/merging region
    L_output_straight_outer = L_total - L_initial_straight_outer - L_curve_outer_dx # 40 - 10 - 15 = 15.0

    # Path smoothing radius for the outer arms' centerlines
    R_outer_bend_smooth = 5.0

    # --- 1. Create the Central Prong (Straight waveguide + Taper) ---
    xs_center_prong = gf.cross_section.cross_section(width=width_prong, layer=LAYER)

    # Position the central prong to taper within the merging region of the outer arms
    # It ends at approx 70% of the way through the curve section
    x_end_central_prong = L_initial_straight_outer + L_curve_outer_dx * 0.7  # 10 + 15 * 0.7 = 20.5 um
    L_center_taper = 4.0  # Length of the taper
    L_center_straight = x_end_central_prong - L_center_taper # 20.5 - 4.0 = 16.5 um

    # Create the straight and tapered segments
    c_center_s = gf.components.straight(length=L_center_straight, cross_section=xs_center_prong)
    # Taper to a very small width (0.01 um) to simulate a sharp point
    c_center_t = gf.components.taper(
        length=L_center_taper,
        width1=width_prong,
        width2=0.01,
        cross_section=xs_center_prong # Inherits layer from cross_section
    )

    # Assemble the central prong into a single component
    central_prong_comp = gf.Component("central_prong_assembled")
    ref_s = central_prong_comp << c_center_s
    ref_t = central_prong_comp << c_center_t
    ref_t.connect("o1", ref_s.ports["o2"]) # Connect taper to straight

    # --- 2. Create the Top and Bottom Merging Arms ---
    # These arms start narrow, curve, and widen to half the output width each.

    # Cross-sections for the start and end of each arm
    xs_start_arm = gf.cross_section.cross_section(width=width_prong, layer=LAYER)
    xs_end_arm = gf.cross_section.cross_section(width=width_output / 2, layer=LAYER) # Each arm contributes half the final width

    # Define the smooth transition between the start and end cross-sections
    transition_arm = gf.path.transition(xs_start_arm, xs_end_arm, width_type='sine')

    # Path for the centerline of the top arm: straight -> curve -> straight
    # Points define the critical vertices of the centerline, gf.path.smooth will add the curves.
    points_top_arm = [
        (0, y_top_center),
        (L_initial_straight_outer, y_top_center),
        (L_initial_straight_outer + L_curve_outer_dx, width_output / 4), # Y-center of the top half of the output waveguide
        (L_total, width_output / 4)
    ]
    P_top_arm = gf.path.smooth(points_top_arm, radius=R_outer_bend_smooth)
    top_arm_comp = gf.path.extrude_transition(P_top_arm, transition_arm)

    # Path for the centerline of the bottom arm: mirrored from the top arm
    points_bottom_arm = [
        (0, y_bottom_center),
        (L_initial_straight_outer, y_bottom_center),
        (L_initial_straight_outer + L_curve_outer_dx, -width_output / 4), # Y-center of the bottom half of the output waveguide
        (L_total, -width_output / 4)
    ]
    P_bottom_arm = gf.path.smooth(points_bottom_arm, radius=R_outer_bend_smooth)
    bottom_arm_comp = gf.path.extrude_transition(P_bottom_arm, transition_arm)

    # Combine the top and bottom arms using a boolean OR operation
    c_outer_merged = gf.boolean(top_arm_comp, bottom_arm_comp, operation="or", layer=LAYER)

    # --- 3. Final Assembly: Combine the outer structure with the central prong ---
    # The central prong is a physical part of the device, so use boolean OR.
    final_device_geom = gf.boolean(c_outer_merged, central_prong_comp, operation="or", layer=LAYER)
    
    # Add the final device geometry to the main component
    c << final_device_geom

    # Optional: Add ports if this device were to be connected to others
    # c.add_port("o1_top", port=top_arm_comp.ports["o1"]) # Example
    # c.add_port("o1_mid", port=central_prong_comp.ports["o1"])
    # c.add_port("o1_bot", port=bottom_arm_comp.ports["o1"])
    # c.add_port("o2", port=c_outer_merged.ports["o2"]) # Output port of the merged section

    # The component is implicitly centered around the origin if all its parts are.
    # We've designed coordinates relative to (0,0) as the center reference.
    # The final bounding box should confirm the footprint.

    return c

# --- Example Usage ---
if __name__ == "__main__":
    device = custom_device_from_image()
    device.write_gds("custom_device_from_image.gds")
    device.show() # Requires KLayout or similar viewer configured
    print(f"Device created: {device.name}.gds")
    print(f"Device bounding box: {device.bbox}") # Check against [40.0, 1.7]