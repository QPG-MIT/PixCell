import gdsfactory as gf
import numpy as np

# Define global layer for the entire device
DEFAULT_LAYER = (1, 0)

@gf.cell
def _make_wavy_stripe_from_points(
    points_global: list[tuple[float, float]],
    w_start: float,
    w_middle: float,
    layer: tuple[int, int],
    radius_smooth: float = 0.5, # Radius for gf.path.smooth
) -> gf.Component:
    """
    Helper function to create a single wavy stripe with varying width
    from a list of global centerline points.
    """
    c = gf.Component()

    # Ensure we are working with a definite list.
    actual_points_global = list(points_global)

    # Explicitly construct lists for path segments to ensure no ambiguity
    # with slice objects, in case that's causing an unexpected interaction
    # in a specific GDSFactory or Python version. This is a highly speculative fix.
    path_points_segment1 = [
        actual_points_global[0],
        actual_points_global[1],
        actual_points_global[2],
    ]
    path_points_segment2 = [
        actual_points_global[2],
        actual_points_global[3],
        actual_points_global[4],
    ]

    # Create path segments using the explicitly constructed lists.
    # gf.path.smooth takes absolute points for defining the path.
    path_segment1 = gf.path.smooth(points=path_points_segment1, radius=radius_smooth)
    path_segment2 = gf.path.smooth(points=path_points_segment2, radius=radius_smooth)

    # Define cross-sections for width variation
    xs_start = gf.cross_section.cross_section(width=w_start, layer=layer)
    xs_middle = gf.cross_section.cross_section(width=w_middle, layer=layer)

    # Define transitions for width change along the path segments
    transition_to_middle = gf.path.transition(xs_start, xs_middle, width_type='sine')
    transition_from_middle = gf.path.transition(xs_middle, xs_start, width_type='sine')

    # Extrude path segments with their respective transitions
    comp_seg1 = gf.path.extrude_transition(path_segment1, transition_to_middle)
    comp_seg2 = gf.path.extrude_transition(path_segment2, transition_from_middle)

    # Add references to the current component 'c'.
    # Each extruded component has its internal (0,0) mapped to the first point of its defining path.
    # We need to move each reference to its actual global starting coordinate.
    ref_seg1 = c << comp_seg1
    ref_seg1.move(actual_points_global[0]) # Move comp_seg1 from its internal (0,0) to global actual_points_global[0]

    ref_seg2 = c << comp_seg2
    ref_seg2.move(actual_points_global[2]) # Move comp_seg2 from its internal (0,0) to global actual_points_global[2]

    # Combine the two segments using a boolean OR operation to create a single, clean stripe.
    # This handles any overlap at the shared middle point seamlessly.
    combined_stripe = gf.boolean(ref_seg1, ref_seg2, operation="or", layer=layer)
    c.add_ref(combined_stripe)
    
    return c

@gf.cell
def wavy_stripes_device() -> gf.Component:
    """
    Creates the device with two vertically mirrored wavy stripes
    within the specified footprint.
    """
    c = gf.Component("wavy_stripes_device")

    # Device footprint dimensions
    total_width = 18.0
    total_height = 3.0

    # Parameters for the stripe geometry
    stripe_amplitude = 0.15           # Max Y-deviation of the centerline from its reference
    stripe_width_at_ends = 1.0        # Width of the stripe at x=0 and x=total_width
    stripe_width_in_middle = 0.6      # Width of the stripe at x=total_width/2

    # Y-coordinates for the centerlines of the bottom and top stripes
    # These are chosen to fit within the total_height and create the desired gap.
    y_centerline_bottom = 0.75
    y_centerline_top = total_height - y_centerline_bottom # Ensures vertical symmetry

    # 1. Define the centerline path points for the bottom stripe
    # This path creates an "up-down-up" wave relative to its centerline.
    bottom_stripe_points = [
        (0, y_centerline_bottom),
        (total_width / 4, y_centerline_bottom + stripe_amplitude),
        (total_width / 2, y_centerline_bottom - stripe_amplitude),
        (3 * total_width / 4, y_centerline_bottom + stripe_amplitude),
        (total_width, y_centerline_bottom),
    ]

    # Create and add the bottom stripe component
    c_bottom_stripe = _make_wavy_stripe_from_points(
        points_global=bottom_stripe_points,
        w_start=stripe_width_at_ends,
        w_middle=stripe_width_in_middle,
        layer=DEFAULT_LAYER,
    )
    c.add_ref(c_bottom_stripe)

    # 2. Define the centerline path points for the top stripe
    # These points are a vertical mirror of the bottom stripe's points across the device's y-centerline.
    top_stripe_points_mirrored = []
    for x, y in bottom_stripe_points:
        mirrored_y = total_height - y
        top_stripe_points_mirrored.append((x, mirrored_y))

    # Create and add the top stripe component
    c_top_stripe = _make_wavy_stripe_from_points(
        points_global=top_stripe_points_mirrored,
        w_start=stripe_width_at_ends,
        w_middle=stripe_width_in_middle,
        layer=DEFAULT_LAYER,
    )
    c.add_ref(c_top_stripe)

    return c

if __name__ == "__main__":
    # Create the device and view it
    device = wavy_stripes_device()
    device.show()

    # Optional: Save the GDS file
    # device.write_gds("wavy_stripes_device.gds")

    # Verify footprint (for automated checks, not visually required)
    # Ensure the entire device fits within 18x3 um
    bbox = device.bbox
    min_x, min_y = bbox[0]
    max_x, max_y = bbox[1]
    
    print(f"Device Bounding Box: min_x={min_x:.3f}, min_y={min_y:.3f}, max_x={max_x:.3f}, max_y={max_y:.3f}")
    print(f"Device Width: {max_x - min_x:.3f} um")
    print(f"Device Height: {max_y - min_y:.3f} um")

    assert np.isclose(max_x - min_x, 18.0, atol=1e-3), f"Device width {max_x - min_x} not close to 18.0"
    assert (max_y - min_y) <= 3.0 + 1e-3, f"Device height {max_y - min_y} exceeds 3.0"
    assert (max_y - min_y) >= 2.4 - 1e-3, f"Device height {max_y - min_y} is too small" # Sanity check for geometry presence
    assert min_x >= 0 - 1e-3, f"Device extends beyond x=0 to {min_x}"
    assert max_x <= 18 + 1e-3, f"Device extends beyond x=18 to {max_x}"
    assert min_y >= 0 - 1e-3, f"Device extends beyond y=0 to {min_y}"
    assert max_y <= 3 + 1e-3, f"Device extends beyond y=3 to {max_y}"