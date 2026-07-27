import gdsfactory as gf
import numpy as np
import os

@gf.cell
def create_wavy_coupler_sinusoidal():
    """
    Creates a wavy directional coupler that visually matches the target image.

    This version uses a path defined by a cosine function to create the smooth,
    continuous curves, which better represents the target than joined S-bends.
    The geometry is still built parametrically from the overall footprint.
    """
    # 1. Define device parameters from footprint and visual analysis
    length = 18.0
    total_height = 3.0
    waveguide_width = 0.8

    # 2. Define the shape of the wave and derive geometric parameters
    # The amplitude is the peak deviation of the centerline from its average y-position.
    # We choose a value that looks visually similar to the target image.
    amplitude = 0.4
    
    # The offset is the average y-position of each waveguide's centerline from y=0.
    # It's derived from the total height, waveguide width, and amplitude.
    # The total height is composed of the center-to-center separation at the ends (2*offset) 
    # plus the additional height from the curves (2*amplitude) and the waveguide width.
    # Total Height = 2 * offset + 2 * amplitude + waveguide_width
    offset = (total_height - waveguide_width - 2 * amplitude) / 2.0

    # Number of points to define the smooth curve
    num_points = 201

    # 3. Generate the points for the paths
    x_coords = np.linspace(0, length, num_points)
    
    # The core cosine shape for the wave (one full period)
    wave_shape = amplitude * np.cos(2 * np.pi * x_coords / length)
    
    # Bottom waveguide centerline (positive cosine shape, shifted down)
    y_coords_bottom = -offset + wave_shape
    points_bottom = list(zip(x_coords, y_coords_bottom))

    # Top waveguide centerline (negative cosine shape, shifted up)
    y_coords_top = +offset - wave_shape
    points_top = list(zip(x_coords, y_coords_top))

    # 4. Create the component and define the cross-section
    c = gf.Component("wavy_coupler_from_image_corrected")
    xs = gf.cross_section.cross_section(width=waveguide_width)
    
    # 5. Create paths, extrude them, and add to the component
    path_top = gf.Path(points_top)
    path_bottom = gf.Path(points_bottom)
    
    wg_top = c << gf.path.extrude(path_top, cross_section=xs)
    wg_bottom = c << gf.path.extrude(path_bottom, cross_section=xs)

    # 6. Add and rename ports for the final device
    # The ports are automatically named 'o1' (start) and 'o2' (end) by extrude.
    c.add_port("o1", port=wg_top.ports["o1"])
    c.add_port("o2", port=wg_top.ports["o2"])
    c.add_port("o3", port=wg_bottom.ports["o1"])
    c.add_port("o4", port=wg_bottom.ports["o2"])
    
    # Center the component horizontally for consistent origin placement
    c.movex(-length / 2.0)

    return c

# Instantiate the final component
device = create_wavy_coupler_sinusoidal()

# Define the output filename
output_filename = "wavy_coupler_corrected.gds"

# Save the component to a GDS file
device.write_gds(output_filename)

# Optional: Display the component in a viewer if available
# device.show()

# Provide confirmation to the user
print(f"Successfully generated GDS file: '{output_filename}'")
print(f"File saved at: {os.path.abspath(output_filename)}")