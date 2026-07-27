import gdsfactory as gf
import pathlib

@gf.cell
def create_chevron_device():
    """
    Creates a device with two symmetric chevron-shaped waveguides based on the
    provided image.
    """
    # 1. Define Device Parameters. We'll use the same footprint as before
    # for a consistent scale.
    length = 18.0
    total_height = 3.0
    wg_width = 0.75
    min_gap = 0.75
    # The 'amplitude' now represents the peak of the chevron corner.
    amplitude = 0.375
    
    # 2. Create the Path for the Top Chevron
    # The centerline y-position for the start and end points.
    y_center_top = min_gap / 2 + wg_width / 2

    # Define the vertices for the path's centerline.
    waypoints = [
        (0, y_center_top),
        (length / 2, y_center_top + amplitude),  # The sharp middle point
        (length, y_center_top),
    ]

    # --- FIX ---
    # The gf.Path constructor takes the list of points as a positional argument,
    # not a keyword argument named 'points'.
    path_top = gf.Path(waypoints)

    # 3. Extrude the Path into a Waveguide Component
    # Define a cross-section with the desired width.
    xs = gf.cross_section.cross_section(width=wg_width)
    
    # Extrude the sharp-cornered path to create the solid geometry.
    chevron_shape = gf.path.extrude(path_top, cross_section=xs)

    # 4. Assemble the Final Device
    c = gf.Component()

    # Add the top chevron shape as a reference.
    ref_top = c.add_ref(chevron_shape)

    # Create the bottom shape by adding another reference and mirroring it.
    ref_bottom = c.add_ref(chevron_shape)
    ref_bottom.mirror(p1=(0, 0), p2=(length, 0)) # Mirror across the x-axis

    # Center the entire component at the origin (0, 0).
    c.movex(-length / 2)
    
    # 5. Add Ports for Connectivity
    c.add_port("o1", port=ref_top.ports["o1"])
    c.add_port("o2", port=ref_top.ports["o2"])
    c.add_port("o3", port=ref_bottom.ports["o1"])
    c.add_port("o4", port=ref_bottom.ports["o2"])

    return c

# To run, verify, and SAVE the script:
if __name__ == "__main__":
    device = create_chevron_device()
    
    # Save the component to a GDS file.
    output_path = pathlib.Path("chevron_device.gds")
    device.write_gds(output_path)
    print(f"GDS file saved to: {output_path.resolve()}")
    
    # Show the component in a viewer.
    device.show()