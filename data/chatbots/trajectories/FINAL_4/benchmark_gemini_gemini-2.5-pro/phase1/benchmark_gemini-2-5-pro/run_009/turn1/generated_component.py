import gdsfactory as gf
import numpy as np

@gf.cell
def create_wavy_device():
    """
    Creates the wavy device geometry based on the provided image and footprint.

    The device consists of two identical, vertically mirrored waveguides
    following a sinusoidal path. The geometry is derived parametrically from
    the overall footprint dimensions and estimated features like waveguide
    width and minimum gap.
    """
    c = gf.Component("wavy_device")

    # 1. Define high-level design parameters from footprint and visual analysis
    footprint_width = 18.0
    footprint_height = 3.0
    
    # Estimate waveguide width and minimum gap from the image proportions.
    # They appear to be roughly equal and take up about 1/4 of the total height each.
    wg_width = 0.75
    min_gap = 0.75
    
    # --- FIX: Define a cross_section object to specify width and layer ---
    xs = gf.cross_section.cross_section(width=wg_width, layer=(1, 0))

    # 2. Calculate the parameters for the sinusoidal path of the top waveguide
    half_length = footprint_width / 2.0

    # The centerline y-coordinate of the top waveguide at its minimum (x=0) is
    # determined by the minimum gap between the two waveguides.
    y_center_min = (min_gap + wg_width) / 2.0

    # The centerline y-coordinate at its maximum (x = +/- half_length) is
    # determined by the total component height.
    y_center_max = footprint_height / 2.0 - wg_width / 2.0

    # The sinusoidal path is modeled as: y(x) = y_offset - amplitude * cos(k*x)
    amplitude = (y_center_max - y_center_min) / 2.0
    y_offset = (y_center_max + y_center_min) / 2.0

    # 3. Generate the points for the path using the calculated parameters
    num_points = 201  # Number of points to define the smooth curve
    x_coords = np.linspace(-half_length, half_length, num_points)
    y_coords = y_offset - amplitude * np.cos(np.pi * x_coords / half_length)
    path_points = np.array([x_coords, y_coords]).T

    # 4. Create a single wavy waveguide component from the generated path
    # This is the fundamental building block.
    path = gf.Path(path_points)
    
    # --- FIX: Pass the cross_section object to extrude() ---
    wavy_waveguide = gf.path.extrude(path, cross_section=xs)

    # 5. Assemble the final device using two references to the building block
    # Add the top waveguide
    wg_top_ref = c << wavy_waveguide

    # Add the bottom waveguide by creating another reference and mirroring it
    wg_bot_ref = c << wavy_waveguide
    wg_bot_ref.mirror(p1=(0, 0), p2=(1, 0))  # Mirror across the x-axis

    # 6. Expose the ports for external connections
    c.add_port(name="o1", port=wg_top_ref.ports["o1"])  # Top left
    c.add_port(name="o2", port=wg_top_ref.ports["o2"])  # Top right
    c.add_port(name="o3", port=wg_bot_ref.ports["o1"])  # Bottom left
    c.add_port(name="o4", port=wg_bot_ref.ports["o2"])  # Bottom right

    return c

# Create an instance of the component to verify its creation
device = create_wavy_device()

# The 'device' variable now holds the GDSFactory component.
# To visualize or save it, you would typically run:
# device.show()
# device.write_gds("wavy_device.gds")