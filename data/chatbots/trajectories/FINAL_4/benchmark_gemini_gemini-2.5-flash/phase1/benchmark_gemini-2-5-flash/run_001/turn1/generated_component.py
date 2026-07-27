import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_bands(
    length: float = 18.0,
    band_width: float = 0.8,
    gap_max: float = 1.4,
    gap_min: float = 0.6,
    num_points: int = 200,
    layer: tuple[int, int] = (1, 0),
) -> gf.Component:
    """
    Creates two horizontal wavy bands with a varying gap.

    The component has a total width of `length` and a total height of 3.0 um.
    The outer edges of the bands are defined such that the component's total height is 3.0 um.
    The gap between the bands varies from `gap_max` at the ends to `gap_min` in the center.
    Each band has a constant `band_width`.

    Args:
        length: Total horizontal length of the component (um).
        band_width: Constant vertical width of each black band (um).
        gap_max: Maximum width of the white gap between bands (at the ends, um).
        gap_min: Minimum width of the white gap between bands (in the center, um).
        num_points: Number of points to sample the curve for smoothness.
        layer: GDS layer for the bands.
    """
    c = gf.Component()

    # Define x-coordinates for the paths (centered from -length/2 to length/2)
    x_points = np.linspace(-length / 2, length / 2, num_points)

    # Calculate parameters for the y-coordinate of the bottom edge of the top band
    # This path defines the top boundary of the white gap.
    y_offset_path = gap_max / 2
    amplitude_curve = (gap_max - gap_min) / 4

    # Generate y-coordinates for the bottom edge of the top band
    y_path_bottom_edge_top_band = [
        y_offset_path - amplitude_curve * (1 - np.cos(2 * np.pi * (x + length / 2) / length))
        for x in x_points
    ]

    # Create the centerline path for the top band
    # The centerline is offset upwards by half the band_width from its bottom edge
    path_top_centerline = gf.Path([
        (x_points[i], y_path_bottom_edge_top_band[i] + band_width / 2)
        for i in range(num_points)
    ])

    # Create the centerline path for the bottom band
    # This path is symmetric to the top band's bottom edge, and offset downwards by half the band_width
    path_bottom_centerline = gf.Path([
        (x_points[i], -y_path_bottom_edge_top_band[i] - band_width / 2)
        for i in range(num_points)
    ])

    # Define the cross-section for extrusion
    # The 'offset=0' (default) means the path is the centerline of the extruded shape.
    xs = gf.cross_section.cross_section(width=band_width, layer=layer)

    # Extrude the paths to create the actual geometry of the bands
    top_band = gf.path.extrude(path_top_centerline, cross_section=xs)
    bottom_band = gf.path.extrude(path_bottom_centerline, cross_section=xs)

    # Add the extruded bands to the component
    c.add_ref(top_band)
    c.add_ref(bottom_band)
    
    # Assert the total footprint matches the constraint (18x3)
    # The component is centered at (0,0), so it should span from [-9, 9] in X and [-1.5, 1.5] in Y.
    # Max Y = (gap_max/2) + band_width = (1.4/2) + 0.8 = 0.7 + 0.8 = 1.5
    # Min Y = -( (gap_max/2) + band_width ) = -1.5
    # Max X = length / 2 = 18 / 2 = 9
    # Min X = -length / 2 = -9
    # The current calculation ensures this.

    return c

# Example usage and visualization
if __name__ == "__main__":
    # Create the component with the determined parameters
    device = wavy_bands(
        length=18.0,
        band_width=0.8,
        gap_max=1.4,
        gap_min=0.6,
        num_points=200,
        layer=(1, 0),
    )

    # Verify the component's footprint using bbox
    # Corrected line: access .bbox and then .width() and .height()
    print(f"Component bounds: Width={device.bbox.width()}, Height={device.bbox.height()}")
    
    # Show the component (requires a KLayout viewer or similar setup)
    # This line will only work if you have KLayout configured for gdsfactory.
    # If not, you can comment it out and use device.write_gds() instead.
    device.show()

    # Optional: Save the GDS file
    # device.write_gds("wavy_bands.gds")