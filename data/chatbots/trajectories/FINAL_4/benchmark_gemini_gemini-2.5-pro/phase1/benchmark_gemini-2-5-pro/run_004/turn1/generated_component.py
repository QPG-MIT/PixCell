import gdsfactory as gf
import numpy as np

@gf.cell
def create_wavy_device():
    """
    Creates a device with two symmetric wavy waveguides based on a sinusoidal path.

    The dimensions are derived from the total footprint [18, 3] um and visual
    proportions observed in the image.
    """
    # High-level design parameters derived from footprint [18, 3]
    length = 18.0
    wg_width = 0.75
    gap = 0.75
    amplitude = 0.375
    
    # Define a cross-section for the waveguide path
    xs = gf.cross_section.cross_section(width=wg_width)
    
    # --- Create the base wavy waveguide component ---
    # We will instantiate and transform this single component to create the final device.
    
    # Generate points for a single period sine wave path centered at y=0
    # The image shows half a sine wave period (one crest or trough),
    # so we use np.sin(np.pi * x / length).
    n_points = 201  # Number of points for a smooth curve
    x_coords = np.linspace(0, length, n_points)
    y_coords = amplitude * np.sin(np.pi * x_coords / length)
    
    points = np.array([x_coords, y_coords]).T
    
    # Create the path and extrude it
    path = gf.Path(points)
    single_wave = gf.path.extrude(path, cross_section=xs)

    # --- Assemble the final device ---
    c = gf.Component("wavy_coupler_device")
    
    # Calculate the vertical offset for the centerlines of the two waveguides.
    # At the ends (x=0), the gap is the vertical distance between the inner edges.
    # The center of the top wg is at +y_offset, bottom at -y_offset.
    # gap = (y_offset - wg_width/2) - (-y_offset + wg_width/2) = 2*y_offset - wg_width
    # Therefore, y_offset = (gap + wg_width) / 2
    y_offset = (gap + wg_width) / 2
    
    # Add the top waveguide
    wave_top = c.add_ref(single_wave)
    wave_top.movey(y_offset)
    
    # Add the bottom waveguide (mirrored across x-axis and shifted down)
    wave_bottom = c.add_ref(single_wave)
    wave_bottom.mirror(p1=(0, 0), p2=(length, 0))
    wave_bottom.movey(-y_offset)
    
    # Center the final component at (0, 0) for good practice.
    # FIX: c.center is a tuple (x, y), which cannot be negated directly.
    # Convert it to a numpy array to perform element-wise negation.
    c.move(-np.array(c.center))

    return c

# --- Main execution block ---
# This part instantiates the component and saves it.
if __name__ == "__main__":
    # Create an instance of the component
    device = create_wavy_device()
    
    # Write the component to a GDS file
    device.write_gds("wavy_device.gds")

    print("Successfully created wavy_device.gds")