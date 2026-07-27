import gdsfactory as gf
from gdsfactory.typings import CrossSectionSpec, LayerSpec 

@gf.cell
def custom_splitter_like(
    wg_width: float = 0.3,          # Width of all waveguides
    initial_gap: float = 0.2,       # Gap between adjacent waveguides on the left
    mid_wg_length: float = 10.0,    # Length of the central waveguide
    overall_length: float = 40.0,   # Total device length (X-dimension)
    overall_height: float = 1.7,    # Total device height (Y-dimension)
    layer: LayerSpec = (1, 0),      # GDS layer for the geometry
    bend_radius: float = 5.0,       # Radius for smoothing curves in gf.path.smooth
) -> gf.Component:
    """
    Recreates a splitter-like geometry with three waveguides.

    The central waveguide is straight, while the top and bottom waveguides
    start parallel, diverge smoothly, and then continue parallel at a wider
    separation, fitting within the specified footprint.

    Args:
        wg_width: The width of the waveguides.
        initial_gap: The gap between the waveguides on the left (input) side.
        mid_wg_length: The length of the central straight waveguide.
        overall_length: The total length of the component (X-dimension).
        overall_height: The total height of the component (Y-dimension).
        layer: The GDS layer for the waveguides.
        bend_radius: The radius used for the smooth bends in the outer waveguides.
    """
    c = gf.Component("custom_splitter_like")

    # Define the cross-section for all waveguides
    xs = gf.cross_section.cross_section(width=wg_width, layer=layer)

    # Calculate Y-coordinates for the centerlines
    # The device is centered vertically at Y=0.
    # The max Y-extent for the device is overall_height / 2 = 0.85
    # The min Y-extent for the device is -overall_height / 2 = -0.85

    # Centerline of outer waveguides at their widest point (right side)
    # The outer edge of the top/bottom waveguide will align with +/- overall_height / 2
    # So, top waveguide centerline at end: overall_height / 2 - wg_width / 2 = 0.85 - 0.15 = 0.7
    # Bottom waveguide centerline at end: -(overall_height / 2 - wg_width / 2) = -0.7
    y_outer_end_centerline = overall_height / 2 - wg_width / 2

    # Centerline of outer waveguides at the start (left side)
    # These are based on the initial_gap and wg_width, relative to the central (Y=0) waveguide
    # Top waveguide centerline at start: (wg_width / 2) + initial_gap + (wg_width / 2) = initial_gap + wg_width = 0.2 + 0.3 = 0.5
    # Bottom waveguide centerline at start: -(initial_gap + wg_width) = -0.5
    y_outer_start_centerline = initial_gap + wg_width

    # 1. Create the middle straight waveguide
    path_mid = gf.path.straight(length=mid_wg_length)
    comp_mid = c << gf.path.extrude(path_mid, xs)
    # Center the middle waveguide at (mid_wg_length / 2, 0)
    comp_mid.center = (mid_wg_length / 2, 0)

    # 2. Create the top waveguide using gf.path.smooth
    # The path starts straight, curves upwards, then straightens out.
    points_top = [
        (0, y_outer_start_centerline),                       # Start point (left input)
        (overall_length * 0.15, y_outer_start_centerline),  # First straight segment (until 15% of length)
        (overall_length * 0.5, y_outer_end_centerline),     # Peak of the curve (mid-length, max Y displacement)
        (overall_length * 0.85, y_outer_end_centerline),    # Straightens out after 85% of length
        (overall_length, y_outer_end_centerline)            # End point (right output)
    ]
    path_top = gf.path.smooth(points_top, radius=bend_radius)
    comp_top = c << gf.path.extrude(path_top, xs)

    # 3. Create the bottom waveguide using gf.path.smooth (mirrored from top)
    points_bottom = [
        (0, -y_outer_start_centerline),
        (overall_length * 0.15, -y_outer_start_centerline),
        (overall_length * 0.5, -y_outer_end_centerline),
        (overall_length * 0.85, -y_outer_end_centerline),
        (overall_length, -y_outer_end_centerline)
    ]
    path_bottom = gf.path.smooth(points_bottom, radius=bend_radius)
    comp_bottom = c << gf.path.extrude(path_bottom, xs)

    # Optional: Add ports for easy connection in larger designs
    c.add_port("o1_mid", port=comp_mid.ports["o1"])
    c.add_port("o2_mid", port=comp_mid.ports["o2"])
    c.add_port("o1_top", port=comp_top.ports["o1"])
    c.add_port("o2_top", port=comp_top.ports["o2"])
    c.add_port("o1_bot", port=comp_bottom.ports["o1"])
    c.add_port("o2_bot", port=comp_bottom.ports["o2"])

    return c

# Example usage and verification
if __name__ == "__main__":
    device = custom_splitter_like()

    # Corrected: Call device.bbox() as a method
    bbox = device.bbox() 
    actual_length = bbox[1][0] - bbox[0][0]
    actual_height = bbox[1][1] - bbox[0][1]

    print(f"--- Device Footprint Verification ---")
    print(f"Expected X-dimension: 40.0 um")
    print(f"Actual X-dimension:   {actual_length:.3f} um")
    print(f"Expected Y-dimension: 1.7 um")
    print(f"Actual Y-dimension:   {actual_height:.3f} um")
    print("-------------------------------------")

    # Uncomment the following lines to write the GDS file and visualize it
    # device.write_gds("custom_splitter_like.gds")
    # gf.show(device) # Requires KLayout installed and configured