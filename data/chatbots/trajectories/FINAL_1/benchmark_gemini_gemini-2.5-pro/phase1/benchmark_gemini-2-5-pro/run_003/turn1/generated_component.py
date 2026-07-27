import gdsfactory as gf
# FIX: Explicitly import the 'bezier' function from the 'gdsfactory.path' module.
from gdsfactory.path import bezier

@gf.cell
def create_trident_splitter():
    """
    Creates a symmetric three-waveguide splitter using parametric GDSFactory functions.

    The device consists of:
    1. A central linear taper.
    2. Two outer arms that curve outwards and simultaneously widen. These are
       constructed by extruding a Bezier path with a varying cross-section.
    """
    # --- Define Parameters based on footprint and image proportions ---
    total_length = 40.0
    total_height = 1.7

    # Central taper parameters
    taper_length = 25.0
    width_center_start = 0.3
    width_center_end = 0.1

    # Outer arm parameters
    width_arm_start = 0.2
    width_arm_end = 0.5
    initial_gap = 0.1

    # --- Calculated Geometric Parameters ---
    # Calculate the final y-position of the arm's centerline based on the
    # total bounding box height.
    # total_height = 2 * (y_centerline_end + width_arm_end / 2)
    y_arm_centerline_end = total_height / 2 - width_arm_end / 2

    # Calculate the initial y-position of the arm's centerline based on the
    # widths and desired gap.
    y_arm_centerline_start = (
        width_center_start / 2 + initial_gap + width_arm_start / 2
    )

    # --- Create Component ---
    c = gf.Component("trident_splitter")

    # 1. Create and place the central taper
    taper_center = gf.components.taper(
        length=taper_length,
        width1=width_center_start,
        width2=width_center_end,
    )
    # Add to component, ensuring its input port ("o1") is at x=0
    ref_center = c << taper_center
    ref_center.movex(-taper_center.xmin)

    # 2. Create the top outer arm using a path and a transition
    # Define a smooth path using a Bezier curve. The control points are chosen
    # to create an S-like bend that starts and ends horizontally.
    control_points = [
        (0, y_arm_centerline_start),
        (total_length / 2, y_arm_centerline_start),
        (total_length / 2, y_arm_centerline_end),
        (total_length, y_arm_centerline_end),
    ]
    
    # FIX: Call the now-imported 'bezier' function directly.
    path = bezier(control_points=control_points)

    # Define the cross-section transition (from narrow to wide)
    xs_start = gf.cross_section.cross_section(width=width_arm_start)
    xs_end = gf.cross_section.cross_section(width=width_arm_end)
    transition = gf.path.transition(
        cross_section1=xs_start, cross_section2=xs_end, width_type="linear"
    )

    # Extrude the path with the transition to create the arm component
    arm_top = gf.path.extrude_transition(path=path, transition=transition)

    # 3. Add top and bottom arms to the main component
    # Add the top arm created above
    c << arm_top

    # Add the bottom arm by creating a new reference to the top arm and mirroring it
    # across the x-axis for perfect symmetry.
    ref_bottom = c << arm_top
    ref_bottom.mirror(p1=(0, 0), p2=(1, 0))

    return c

# --- Main execution block to generate and display the GDS ---
if __name__ == "__main__":
    device = create_trident_splitter()
    device.show(show_ports=False)

    # Optional: Verify the footprint
    print(f"Device created with footprint (dx, dy): ({device.dx:.2f}, {device.dy:.2f})")