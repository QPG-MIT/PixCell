import gdsfactory as gf
import numpy as np

@gf.cell
def wavy_bands(
    length: float = 18.0,
    height: float = 3.0,
    band_width: float = 0.5,
    gap_min: float = 0.4,
    gap_max: float = 1.0,
    num_points: int = 100,
    layer: gf.typings.Layer = (1, 0),
) -> gf.Component:
    """
    Creates two wavy parallel bands forming a bottleneck shape in the middle.

    The bands maintain a constant width and the gap between them varies
    sinusoidally, being narrowest in the middle and widest at the ends.
    The total geometry is centered vertically within the specified height.

    Args:
        length: Total length of the device (x-dimension).
        height: Total height of the device bounding box (y-dimension).
        band_width: Width of each black band.
        gap_min: Minimum gap between the two bands (at x=length/2).
        gap_max: Maximum gap between the two bands (at x=0 and x=length).
        num_points: Number of points to sample the cosine path for smoothness.
        layer: GDS layer for the bands.
    """
    c = gf.Component()

    # Define the cross-section for extruding the paths
    xs = gf.cross_section.cross_section(width=band_width, layer=layer)

    # Calculate parameters for the gap function: GAP(x) = A * cos(pi * x / length) + B
    # The gap function describes the vertical distance between the inner edges of the two bands.
    A_gap = (gap_max - gap_min) / 2
    B_gap = (gap_max + gap_min) / 2

    # Midline of the entire device (y-axis center)
    mid_y = height / 2

    # Generate x-coordinates for sampling the paths
    x_coords = np.linspace(0, length, num_points)

    # Calculate the y-values for the varying gap
    y_gap_values = A_gap * np.cos(np.pi * x_coords / length) + B_gap

    # Calculate y-coordinates for the centerline of the top band
    # This is (mid_y + half of the gap + half of the band_width)
    y_top_center_coords = mid_y + y_gap_values / 2 + band_width / 2

    # Calculate y-coordinates for the centerline of the bottom band
    # This is (mid_y - half of the gap - half of the band_width)
    y_bottom_center_coords = mid_y - y_gap_values / 2 - band_width / 2

    # Create Path objects from the sampled coordinates
    path_top_center = gf.Path(list(zip(x_coords, y_top_center_coords)))
    path_bottom_center = gf.Path(list(zip(x_coords, y_bottom_center_coords)))

    # Extrude the paths using the defined cross-section to create the black bands
    top_band = gf.path.extrude(path_top_center, cross_section=xs)
    bottom_band = gf.path.extrude(path_bottom_center, cross_section=xs)

    # Add the extruded bands as references to the main component
    c.add_ref(top_band)
    c.add_ref(bottom_band)

    return c

if __name__ == "__main__":
    # Create the component with the specified parameters
    device = wavy_bands(
        length=18.0,
        height=3.0,
        band_width=0.5,
        gap_min=0.4,
        gap_max=1.0,
        num_points=100,
    )

    # Save the component to a GDSII file
    device.write_gds("wavy_bands.gds")

    # FIX: Call device.bbox() as a method to get the bounding box array.
    bbox = device.bbox() # Changed from device.bbox to device.bbox()
    print(f"Component bounding box: {bbox}")
    
    assert np.isclose(bbox[0, 0], 0.0), f"Expected min X 0.0, got {bbox[0,0]}"
    assert np.isclose(bbox[1, 0], 18.0), f"Expected max X 18.0, got {bbox[1,0]}"
    assert np.isclose(bbox[0, 1], 0.5), f"Expected min Y 0.5, got {bbox[0,1]}"
    assert np.isclose(bbox[1, 1], 2.5), f"Expected max Y 2.5, got {bbox[1,1]}"
    
    print("\nDevice 'wavy_bands.gds' created successfully, fitting within the [18, 3] footprint.")