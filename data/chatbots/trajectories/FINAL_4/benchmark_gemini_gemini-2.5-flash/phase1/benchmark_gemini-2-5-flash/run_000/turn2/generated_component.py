import gdsfactory as gf
from gdsfactory.typings import LayerSpec

@gf.cell
def create_single_wavy_band_smooth(
    width: float = 0.8, 
    points: list[tuple[float, float]] = None, 
    layer: LayerSpec = (1, 0),
    smooth_radius: float = 1.0 # Added parameter to control smoothness
) -> gf.Component:
    """
    Creates a single wavy band using gf.path.smooth.

    Args:
        width: The width of the band.
        points: A list of (x, y) coordinates defining the path for the centerline.
                Expected to be 3 points: [(start_x, start_y), (mid_x, mid_y), (end_x, end_y)].
        layer: GDS layer for the band.
        smooth_radius: The minimum bend radius used for smoothing the path.
                       A smaller radius can make the curve sharper, a larger one smoother.
    
    Returns:
        A gdsfactory Component representing the wavy band.
    """
    if points is None:
        raise ValueError("points list must be provided for create_single_wavy_band_smooth")
    
    c = gf.Component()
    xs = gf.cross_section.cross_section(width=width, layer=layer)
    
    # Create the path using smooth interpolation with specified radius
    path = gf.path.smooth(points=points, radius=smooth_radius)

    # Extrude the path to create the component geometry
    band = gf.path.extrude(path, cross_section=xs)
    c.add_ref(band)
    
    # Add ports from the extruded path to the component
    # gf.path.extrude with default cross_section creates 'o1' and 'o2' ports
    c.add_port("o1", port=band.ports["o1"]) 
    c.add_port("o2", port=band.ports["o2"])
    
    return c

@gf.cell
def wavy_channel_device_v2() -> gf.Component:
    """
    Recreates the geometry from the provided image using gf.path.smooth.
    The device is designed to fit a footprint of [18, 3] micrometers.

    Returns:
        A gdsfactory Component containing the two wavy bands.
    """
    c = gf.Component("wavy_channel_device_v2")
    
    # Device parameters derived from image analysis and footprint constraint
    total_length = 18.0  # From footprint_um[0]
    total_height = 3.0   # From footprint_um[1]
    
    band_width = 0.8     # Estimated width of the black bands from image
    layer = (1, 0)
    smooth_radius = 1.0  # Tunable parameter for curve smoothness

    # Calculate H_wave (vertical excursion of the centerline from its start/end Y to its midpoint Y)
    # Target middle gap = 0.2 um
    # Gap_middle = total_height - 2*band_width - 2*H_wave
    # 0.2 = 3.0 - 2*0.8 - 2*H_wave
    # 0.2 = 3.0 - 1.6 - 2*H_wave
    # 0.2 = 1.4 - 2*H_wave
    # 2*H_wave = 1.2 => H_wave = 0.6
    H_wave = 0.6
    
    # Calculate the Y-coordinates for the centerlines at the start and end of the device.
    # These ensure the overall footprint is respected.
    Y_start_top_center = total_height - band_width / 2  # 3.0 - 0.4 = 2.6
    Y_start_bottom_center = band_width / 2              # 0.4

    # Define the 3 control points for the centerline of the top band (valley shape)
    # (x_start, y_start), (x_mid, y_mid), (x_end, y_end)
    top_band_points = [
        (0, Y_start_top_center),
        (total_length / 2, Y_start_top_center - H_wave), # Dips down in the middle
        (total_length, Y_start_top_center)
    ]
    
    # Define the 3 control points for the centerline of the bottom band (hill shape)
    # (x_start, y_start), (x_mid, y_mid), (x_end, y_end)
    bottom_band_points = [
        (0, Y_start_bottom_center),
        (total_length / 2, Y_start_bottom_center + H_wave), # Rises up in the middle
        (total_length, Y_start_bottom_center)
    ]
    
    # Create and add the top band component using the smooth path
    top_band_ref = c << create_single_wavy_band_smooth(
        width=band_width,
        points=top_band_points,
        layer=layer,
        smooth_radius=smooth_radius
    )
    
    # Create and add the bottom band component using the smooth path
    bottom_band_ref = c << create_single_wavy_band_smooth(
        width=band_width,
        points=bottom_band_points,
        layer=layer,
        smooth_radius=smooth_radius
    )
    
    # Add ports to the main component for potential connection in larger designs
    c.add_port("o1_top", port=top_band_ref.ports["o1"])
    c.add_port("o2_top", port=top_band_ref.ports["o2"])
    c.add_port("o1_bot", port=bottom_band_ref.ports["o1"])
    c.add_port("o2_bot", port=bottom_band_ref.ports["o2"])
    
    return c

# Example usage to visualize and save the GDS
if __name__ == "__main__":
    device = wavy_channel_device_v2()
    
    # Print the bounding box to verify the footprint
    print(f"Device bounds: x_min={device.xmin}, y_min={device.ymin}, x_max={device.xmax}, y_max={device.ymax}")
    # Expected output: x_min=0.0, y_min=0.0, x_max=18.0, y_max=3.0

    # Write the GDS file
    device.write_gds("wavy_channel_device_smooth.gds")

    # To visualize the GDS file (requires KLayout or similar GDS viewer installed for gf.show)
    # gf.show(device)