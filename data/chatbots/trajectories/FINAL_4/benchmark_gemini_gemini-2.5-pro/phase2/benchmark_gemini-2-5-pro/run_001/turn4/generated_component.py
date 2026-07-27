import gdsfactory as gf
import numpy as np
import pathlib

@gf.cell
def create_wavy_coupler():
    """
    Creates a device with two symmetric, wavy waveguides.
    
    This version refines the curve from a simple sine wave to a full-period
    cosine wave. This ensures the waveguides have zero slope at the input/output
    ports, perfectly matching the target image's smooth, adiabatic-like shape.
    """
    # 1. Define Device Parameters from Footprint and Visuals
    length = 18.0
    total_height = 3.0
    
    # Estimate waveguide width and central gap from the target image proportions.
    # They appear roughly equal, and together they make up the narrowest part.
    wg_width = 0.75
    gap_center = 0.75

    # 2. Calculate Key Y-Coordinates for the Top Waveguide's Centerline
    # The device is symmetric around the x-axis (y=0).
    
    # Centerline y-position at the device's middle (x = length/2).
    y_center_mid = gap_center / 2 + wg_width / 2
    
    # The device's top edge is at y = total_height / 2.
    # The centerline at the ends is a half-width below this edge.
    y_center_ends = total_height / 2 - wg_width / 2

    # The amplitude is the total vertical deviation of the centerline.
    amplitude = y_center_ends - y_center_mid

    # 3. Generate a Smooth Path using a Full Cosine Wave
    # This is the key change to match the target's zero-slope endpoints.
    num_points = 201
    x_coords = np.linspace(0, length, num_points)
    
    # The formula for a raised cosine creates a path that starts and ends
    # with zero slope, dipping in the middle.
    # y(x) = y_start + (amplitude/2) * (cos(2*pi*x/L) - 1)
    # This traces a path from y_start down by 'amplitude' and back up.
    
    y_deviation = (amplitude / 2) * (np.cos(2 * np.pi * x_coords / length) - 1)
    y_coords_top = y_center_ends + y_deviation
    
    # Combine coordinates into a list of waypoints for the Path object.
    waypoints = list(zip(x_coords, y_coords_top))

    # 4. Create the Path and Extrude it into a Component
    path_top = gf.Path(waypoints)
    
    # Define the cross-section for extrusion.
    xs = gf.cross_section.cross_section(width=wg_width)
    
    # Extrude the path to create the solid waveguide shape.
    wave_shape = gf.path.extrude(path_top, cross_section=xs)

    # 5. Assemble the Final Symmetrical Device
    c = gf.Component("wavy_coupler_cosine")

    # Add the top waveguide as a reference.
    ref_top = c.add_ref(wave_shape)

    # Add the bottom waveguide by mirroring the top one.
    ref_bottom = c.add_ref(wave_shape)
    ref_bottom.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across x-axis

    # Center the entire component at the origin (0, 0).
    c.movex(-length / 2)
    
    # 6. Add Ports for Connectivity
    # The ports are automatically created at the ends of the extruded path.
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