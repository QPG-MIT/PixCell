import gdsfactory as gf
import numpy as np
import pathlib

@gf.cell
def create_wavy_coupler():
    """
    Creates a device with two symmetric, wavy waveguides, matching the smooth
    curves of the target image.
    
    This version transitions from the previous sharp 'chevron' shape to a
    smooth sine-wave based curve.
    """
    # 1. Define Device Parameters based on the footprint and visual inspection.
    length = 18.0
    wg_width = 0.75
    
    # Amplitude is the peak vertical deviation of the waveguide's centerline.
    # This controls how "wavy" the guides are.
    amplitude = 0.375
    
    # To maintain symmetry and control the device height, we define the gap
    # at the narrowest point (the center). Let's make it equal to the wg_width.
    gap_center = 0.75

    # 2. Calculate Key Y-Coordinates for the Top Waveguide's Centerline
    # The device is symmetric around the x-axis (y=0).
    # The centerline y-position at the device's middle (x = length/2).
    y_center_mid = gap_center / 2 + wg_width / 2
    
    # The centerline y-position at the device's ends (x=0, x=length).
    y_center_ends = y_center_mid + amplitude

    # 3. Generate a Smooth Path using a Sine Wave
    # We will generate a list of points to define the smooth path, replacing
    # the previous 3-point list.
    num_points = 201  # Use a high number of points for a smooth approximation.
    x_coords = np.linspace(0, length, num_points)
    
    # The core of the new shape: a sine wave that creates a smooth dip.
    # The formula y(x) = y_end - amplitude * sin(pi*x/L) creates a path
    # that starts at y_end, dips by 'amplitude' in the middle, and returns to y_end.
    theta = np.pi * x_coords / length
    y_coords_top = y_center_ends - amplitude * np.sin(theta)
    
    # Combine the coordinates into a list of waypoints for the Path object.
    waypoints = list(zip(x_coords, y_coords_top))

    # 4. Create the Path and Extrude it into a Component
    path_top = gf.Path(waypoints)
    
    # Define the cross-section for extrusion.
    xs = gf.cross_section.cross_section(width=wg_width)
    
    # Extrude the path to create the solid waveguide shape.
    wave_shape = gf.path.extrude(path_top, cross_section=xs)

    # 5. Assemble the Final Symmetrical Device
    c = gf.Component("wavy_coupler")

    # Add the top waveguide as a reference.
    ref_top = c.add_ref(wave_shape)

    # Add the bottom waveguide by creating a mirrored copy of the same shape.
    ref_bottom = c.add_ref(wave_shape)
    # Mirror across the horizontal x-axis to create the bottom half.
    ref_bottom.mirror(p1=(0, 0), p2=(1, 0))

    # Center the entire component at the origin (0, 0).
    # The component is already vertically centered due to the mirroring.
    # We only need to shift it horizontally.
    c.movex(-length / 2)
    
    # 6. Add Ports for Connectivity
    c.add_port("o1", port=ref_top.ports["o1"])
    c.add_port("o2", port=ref_top.ports["o2"])
    c.add_port("o3", port=ref_bottom.ports["o1"])
    c.add_port("o4", port=ref_bottom.ports["o2"])

    return c

# To run, verify, and SAVE the script:
if __name__ == "__main__":
    device = create_wavy_coupler()
    
    # Save the component to a GDS file.
    output_path = pathlib.Path("wavy_coupler.gds")
    device.write_gds(output_path)
    print(f"GDS file saved to: {output_path.resolve()}")
    
    # Show the component in a viewer.
    device.show()