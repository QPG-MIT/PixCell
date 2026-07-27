import gdsfactory as gf

@gf.cell
def single_waveguide_arc(
    bend_size: tuple[float, float], cross_section="strip"
) -> gf.Component:
    """
    Creates a single waveguide arc composed of two S-bends.
    The path starts at (0,0), peaks at (dx, dy), and returns to y=0 at (2*dx, 0).

    Args:
        bend_size: A tuple (dx, dy) where dx is the horizontal length of a
                   single S-bend and dy is its vertical displacement.
        cross_section: The cross_section of the waveguide.
    """
    c = gf.Component()
    dx, dy = bend_size

    # An arc is formed by one S-bend going up and another going down.
    s_bend_up = gf.components.bend_s(size=(dx, dy), cross_section=cross_section)
    s_bend_down = gf.components.bend_s(size=(dx, -dy), cross_section=cross_section)

    ref1 = c << s_bend_up
    ref2 = c << s_bend_down
    ref2.connect("o1", ref1.ports["o2"])

    c.add_port("o1", port=ref1.ports["o1"])
    c.add_port("o2", port=ref2.ports["o2"])
    return c


@gf.cell
def create_device() -> gf.Component:
    """
    Creates a component with two waveguides that diverge from each other at the
    center and then converge back to their original separation.

    This matches the target image by creating one arc-shaped waveguide and then
    placing a vertically mirrored copy of it to form the symmetric pair.
    """
    # 1. Define device parameters from footprint and visual inspection.
    footprint_width = 18.0
    footprint_height = 3.0
    waveguide_width = 0.5

    # Estimate the gap between the waveguides at their closest point (center).
    # Visually, it's about the same as the waveguide width.
    center_gap = 0.5

    # Define a cross_section for the waveguides. A minimum bend radius is
    # specified to ensure the geometry is manufacturable and smooth.
    xs = gf.cross_section.cross_section(width=waveguide_width, radius=5.0)

    # 2. Calculate geometric parameters for the constituent S-bends.
    # dx is the horizontal length of one S-bend, which is half the device width.
    dx = footprint_width / 2

    # y_outer is the centerline y-coordinate at the device's start and end.
    y_outer = (footprint_height / 2) - (waveguide_width / 2)

    # y_inner is the centerline y-coordinate at the device's center.
    y_inner = center_gap / 2

    # dy is the total vertical travel for a single S-bend to go from the
    # outer position to the inner position.
    dy = y_outer - y_inner

    # 3. Instantiate the base arc-shaped waveguide component.
    arc_wg = single_waveguide_arc(bend_size=(dx, dy), cross_section=xs)

    # 4. Assemble the final device from two instances of the arc waveguide.
    c = gf.Component("diverging_waveguides_device")

    # Add the bottom waveguide.
    # It is shifted to be centered horizontally at x=0 and to have its
    # endpoints at y=-y_outer and its peak at y=-y_inner.
    ref_bottom = c << arc_wg
    ref_bottom.move((-dx, -y_outer))

    # Add the top waveguide, which is a mirrored copy of the bottom one.
    # It is also shifted to be centered horizontally at x=0 and to have its
    # endpoints at y=+y_outer and its trough at y=+y_inner.
    ref_top = c << arc_wg
    ref_top.mirror(p1=(0, 0), p2=(1, 0))  # Mirror vertically across x-axis
    ref_top.move((-dx, y_outer))

    return c


# Main execution block for testing and saving the GDS file.
if __name__ == "__main__":
    # Create an instance of the final component.
    device_to_save = create_device()

    # Save the GDS file to disk in the current directory.
    output_path = device_to_save.write_gds("final_device.gds")
    
    print(f"Successfully wrote GDS file to: {output_path}")

    # To display the component if running in an interactive environment (like Jupyter):
    # device_to_save.show()