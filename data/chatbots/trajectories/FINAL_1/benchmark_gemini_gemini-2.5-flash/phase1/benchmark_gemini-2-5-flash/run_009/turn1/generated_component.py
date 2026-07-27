import gdsfactory as gf
import numpy as np

@gf.cell
def custom_splitter_like_device():
    """
    Recreates the geometry shown in the image using GDSFactory parametric functions.

    The device consists of three parallel waveguides at the input:
    - A central straight waveguide.
    - Two outer waveguides (top and bottom) that start straight, then gently curve outwards
      while simultaneously increasing in width, and finally continue straight with the wider width.

    The geometry is designed to fit within the specified footprint_um of [40.0, 1.7].
    """
    c = gf.Component()

    # --- Parameters ---
    # Initial waveguide and gap dimensions
    w0 = 0.4  # Initial width of all waveguides
    g0 = 0.05 # Initial gap between central and outer waveguides

    # Final width of outer waveguides (after tapering)
    w_final_outer = 0.5 # Slightly wider than initial width

    # Lengths for straight and curved sections
    L_center_wg = 18.0          # Length of the central straight waveguide
    L_straight_in_outer = 15.0  # Initial straight length for outer waveguides
    L_straight_out_outer = 15.0 # Final straight length for outer waveguides (after bend)

    # Parameters for the Euler bend in outer waveguides (gentle curve)
    # A large radius and small angle create a very subtle, almost straight divergence.
    R_euler = 100.0 # Large radius for subtle curvature
    A_euler = 0.5   # Small angle (in degrees) for minimal divergence

    # --- Cross-sections ---
    # Define the initial and final cross-sections for the waveguides
    xs_initial = gf.cross_section.cross_section(width=w0, layer=(1, 0))
    xs_final_outer = gf.cross_section.cross_section(width=w_final_outer, layer=(1, 0))
    
    # --- 1. Central Waveguide ---
    # Create the central straight waveguide.
    # By default, gf.components.straight's 'o1' port is at (0,0) and 'o2' at (length,0).
    center_wg = c << gf.components.straight(length=L_center_wg, cross_section=xs_initial)

    # --- 2. Top Outer Waveguide ---
    # Calculate the y-offset for the centerline of the top waveguide's input port.
    # This places it relative to the central waveguide's y=0.
    y_offset_top = w0 / 2 + g0 + w0 / 2

    # Segment 1: Initial straight section with constant width (w0)
    # Create a path for the straight segment.
    path_seg1_top = gf.path.straight(length=L_straight_in_outer)
    # Extrude the path with the initial cross-section.
    comp_seg1_top = c << gf.path.extrude(path_seg1_top, cross_section=xs_initial)
    # Move the entire component instance to its correct y-position.
    comp_seg1_top.movey(y_offset_top)

    # Segment 2: Euler bend with width transition from w0 to w_final_outer
    # Create a path for the Euler bend.
    path_seg2_top = gf.path.euler(radius=R_euler, angle=A_euler)
    # Create a transition cross-section that smoothly changes from initial to final width.
    xs_transition_top = gf.path.transition(xs_initial, xs_final_outer, width_type='sine') # 'sine' provides smooth tapering
    # Extrude the bend path with the transitioning cross-section.
    comp_seg2_top = c << gf.path.extrude_transition(path_seg2_top, xs_transition_top)
    # Connect the start of this segment to the end of the previous segment.
    comp_seg2_top.connect("o1", comp_seg1_top.ports["o2"])

    # Segment 3: Final straight section with constant wider width (w_final_outer)
    # Create a path for the final straight segment.
    path_seg3_top = gf.path.straight(length=L_straight_out_outer)
    # Extrude with the final wider cross-section.
    comp_seg3_top = c << gf.path.extrude(path_seg3_top, cross_section=xs_final_outer)
    # Connect to the end of the bend segment.
    comp_seg3_top.connect("o1", comp_seg2_top.ports["o2"])

    # --- 3. Bottom Outer Waveguide (Symmetric to Top) ---
    # Calculate the y-offset for the centerline of the bottom waveguide's input port (negative of top).
    y_offset_bottom = -(w0 / 2 + g0 + w0 / 2)

    # Segment 1: Initial straight section
    path_seg1_bottom = gf.path.straight(length=L_straight_in_outer)
    comp_seg1_bottom = c << gf.path.extrude(path_seg1_bottom, cross_section=xs_initial)
    comp_seg1_bottom.movey(y_offset_bottom)

    # Segment 2: Euler bend with width transition (negative angle for bottom bend)
    path_seg2_bottom = gf.path.euler(radius=R_euler, angle=-A_euler) # Negative angle mirrors the top bend
    xs_transition_bottom = gf.path.transition(xs_initial, xs_final_outer, width_type='sine')
    comp_seg2_bottom = c << gf.path.extrude_transition(path_seg2_bottom, xs_transition_bottom)
    comp_seg2_bottom.connect("o1", comp_seg1_bottom.ports["o2"])

    # Segment 3: Final straight section
    path_seg3_bottom = gf.path.straight(length=L_straight_out_outer)
    comp_seg3_bottom = c << gf.path.extrude(path_seg3_bottom, cross_section=xs_final_outer)
    comp_seg3_bottom.connect("o1", comp_seg2_bottom.ports["o2"])

    # --- Expose Ports ---
    # Expose the input ports (all at x=0, with their respective y-offsets)
    c.add_port("o1", port=center_wg.ports["o1"])
    c.add_port("o2", port=comp_seg1_top.ports["o1"])
    c.add_port("o3", port=comp_seg1_bottom.ports["o1"])

    # Expose the output ports
    c.add_port("o4", port=center_wg.ports["o2"])
    c.add_port("o5", port=comp_seg3_top.ports["o2"])
    c.add_port("o6", port=comp_seg3_bottom.ports["o2"])

    # --- Fix for ValueError: Found off-grid instances ---
    # The Euler bends and width transitions can generate floating-point coordinates
    # that are not perfectly aligned to the GDS grid, leading to off-grid instances.
    # Flattening the component converts all sub-components into raw polygons within 'c',
    # effectively resolving the off-grid instance issue for GDS export.
    c.flatten()

    return c

# --- Main execution block ---
if __name__ == "__main__":
    device = custom_splitter_like_device()

    # Calculate the actual footprint to verify against the constraint [40.0, 1.7]
    # FIX: gf.Component.bbox is a method and needs to be called with ()
    bbox = device.bbox() 
    x_min, y_min = bbox[0]
    x_max, y_max = bbox[1]
    actual_x_size = x_max - x_min
    actual_y_size = y_max - y_min

    print(f"Calculated device footprint (X, Y): ({actual_x_size:.2f} um, {actual_y_size:.2f} um)")
    print(f"Target device footprint (X, Y): (40.0 um, 1.7 um)")

    # Write the component to a GDSII file
    device.write_gds("custom_splitter_device.gds")
    print("GDS file 'custom_splitter_device.gds' created.")
    
    # Optional: Display the device (requires KLayout or similar viewer configured)
    # device.show()