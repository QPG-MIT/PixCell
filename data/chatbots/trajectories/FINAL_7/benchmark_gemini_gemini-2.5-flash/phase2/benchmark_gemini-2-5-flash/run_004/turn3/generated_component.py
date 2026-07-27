import gdsfactory as gf

# Define a default layer for all geometries
LAYER = (1, 0)

@gf.cell
def inner_link_unit(
    pad_width: float = 0.5,
    pad_length: float = 0.5,
    center_bar_width: float = 0.2,
    center_bar_length: float = 0.2,
    outer_arm_straight_length: float = 0.1,
    outer_arm_taper_out_length: float = 0.2,
    outer_arm_taper_out_half_width_increase: float = 0.2, # half-width increase from half_w_pad
    outer_arm_taper_in_length: float = 0.2,
    outer_arm_narrow_point_half_width: float = 0.05, # half-width at the end of the second taper
    outer_arm_tip_length: float = 0.05,
    layer: tuple = LAYER
) -> gf.Component:
    """
    Creates one complete inner chain-link-like structure as a single polygon.
    The component is centered at (0,0).
    
    Args:
        pad_width: Width of the square-like pads.
        pad_length: Length of the square-like pads along x-axis.
        center_bar_width: Width of the connecting bar between pads.
        center_bar_length: Length of the connecting bar between pads.
        outer_arm_straight_length: Length of the straight segment immediately after the pad.
        outer_arm_taper_out_length: Length of the section that tapers outwards.
        outer_arm_taper_out_half_width_increase: Amount of half-width increase in the outward taper.
        outer_arm_taper_in_length: Length of the section that tapers inwards.
        outer_arm_narrow_point_half_width: Half-width at the end of the inward taper (before the final tip).
        outer_arm_tip_length: Length of the final sharp tip.
        layer: GDS layer for the polygon.
    """
    c = gf.Component("inner_link_unit")

    # Calculate half-widths for various sections
    half_w_cb = center_bar_width / 2
    half_w_pad = pad_width / 2
    half_w_taper_out_max = half_w_pad + outer_arm_taper_out_half_width_increase
    
    # Ensure calculated narrow point width is sensible (e.g., non-negative)
    half_w_narrow_point = max(0.01, outer_arm_narrow_point_half_width) 

    # Calculate x-coordinates for the segments, relative to center (0,0)
    # Right half x-coordinates (building up from center to right)
    x_mid_right_bar = center_bar_length / 2
    x_right_pad_start = x_mid_right_bar # Left edge of right pad
    x_right_pad_end = x_right_pad_start + pad_length # Right edge of right pad
    x_right_outer_straight_end = x_right_pad_end + outer_arm_straight_length
    x_right_taper_out_end = x_right_outer_straight_end + outer_arm_taper_out_length
    x_right_taper_in_end = x_right_taper_out_end + outer_arm_taper_in_length
    x_right_tip = x_right_taper_in_end + outer_arm_tip_length

    # Left half x-coordinates (symmetrical, negative of right side, but ordered for polygon)
    x_mid_left_bar = -center_bar_length / 2
    x_left_pad_start = x_mid_left_bar # Right edge of left pad
    x_left_pad_end = x_left_pad_start - pad_length # Left edge of left pad
    x_left_outer_straight_end = x_left_pad_end - outer_arm_straight_length
    x_left_taper_out_end = x_left_outer_straight_end - outer_arm_taper_out_length
    x_left_taper_in_end = x_left_outer_straight_end - outer_arm_taper_out_length - outer_arm_taper_in_length
    x_left_tip = x_left_taper_in_end - outer_arm_tip_length


    # Define polygon points (clockwise order, starting from rightmost tip)
    points = []
    
    # Right side, clockwise, starting from tip (y=0)
    points.append((x_right_tip, 0))
    points.append((x_right_taper_in_end, -half_w_narrow_point)) # Bottom-right of narrow part before tip
    points.append((x_right_taper_out_end, -half_w_taper_out_max)) # Bottom-right of widest part
    points.append((x_right_outer_straight_end, -half_w_pad)) # Bottom-right of straight after pad
    points.append((x_right_pad_end, -half_w_pad)) # Bottom-right of pad
    points.append((x_right_pad_start, -half_w_cb)) # Bottom-left of pad (connects to center bar)
    points.append((x_mid_right_bar, -half_w_cb)) # Bottom-right of center bar

    # Left side, clockwise
    points.append((x_mid_left_bar, -half_w_cb)) # Bottom-left of center bar
    points.append((x_left_pad_start, -half_w_cb)) # Bottom-right of left pad (connects to center bar)
    points.append((x_left_pad_end, -half_w_pad)) # Bottom-left of left pad
    points.append((x_left_outer_straight_end, -half_w_pad)) # Bottom-left of straight after pad
    points.append((x_left_taper_out_end, -half_w_taper_out_max)) # Bottom-left of widest part
    points.append((x_left_taper_in_end, -half_w_narrow_point)) # Bottom-left of narrow part before tip
    points.append((x_left_tip, 0)) # Left tip

    # Left side, counter-clockwise (going up)
    points.append((x_left_taper_in_end, half_w_narrow_point))
    points.append((x_left_taper_out_end, half_w_taper_out_max))
    points.append((x_left_outer_straight_end, half_w_pad))
    points.append((x_left_pad_end, half_w_pad)) # Top-left of left pad
    points.append((x_left_pad_start, half_w_cb)) # Top-right of left pad (connects to center bar)
    points.append((x_mid_left_bar, half_w_cb)) # Top-left of center bar

    # Right side, counter-clockwise (going up)
    points.append((x_mid_right_bar, half_w_cb)) # Top-right of center bar
    points.append((x_right_pad_start, half_w_cb)) # Top-left of right pad (connects to center bar)
    points.append((x_right_pad_end, half_w_pad)) # Top-right of right pad
    points.append((x_right_outer_straight_end, half_w_pad))
    points.append((x_right_taper_out_end, half_w_taper_out_max))
    points.append((x_right_taper_in_end, half_w_narrow_point))
    # Implicitly connects back to (x_right_tip, 0)

    c.add_polygon(points, layer=layer)
    return c


@gf.cell
def custom_device(
    footprint_um: list = [3.0, 5.5],
    frame_thickness: float = 0.15,
    inner_vertical_gap: float = 0.6,
    inner_unit_params: dict = None, # Parameters for inner_link_unit
    layer: tuple = LAYER
) -> gf.Component:
    """
    Creates the device matching the target image, consisting of an
    elliptical frame and two inner symmetrical chain-link-like structures.
    
    Args:
        footprint_um: [width, height] of the overall device.
        frame_thickness: Thickness of the elliptical outer frame.
        inner_vertical_gap: Vertical gap between the two inner chain-link units.
        inner_unit_params: Dictionary of parameters to pass to `inner_link_unit`.
        layer: GDS layer for all geometries.
    """
    c = gf.Component("complex_device")

    # 1. Outer Elliptical Frame
    x_radius = footprint_um[0] / 2
    y_radius = footprint_um[1] / 2

    outer_ellipse = gf.components.ellipse(radii=(x_radius, y_radius), layer=layer)
    inner_ellipse = gf.components.ellipse(
        radii=(x_radius - frame_thickness, y_radius - frame_thickness), layer=layer
    )
    elliptical_frame_ref = c << gf.boolean(outer_ellipse, inner_ellipse, operation="not", layer=layer)
    elliptical_frame_ref.center = (0,0)

    # 2. Inner Chain-Link Structures
    if inner_unit_params is None:
        inner_unit_params = {} # Use default parameters from inner_link_unit

    # Instantiate a temporary unit to get its bounds for positioning
    temp_unit_for_bounds = inner_link_unit(**inner_unit_params)
    # The inner_link_unit is centered at (0,0) and symmetrical.
    # Its max_y corresponds to the half-height of the unit.
    unit_half_height = temp_unit_for_bounds.ymax 

    # Position the top unit
    y_top_pos = unit_half_height + inner_vertical_gap / 2
    inner_unit_top_ref = c << inner_link_unit(**inner_unit_params, layer=layer)
    inner_unit_top_ref.center = (0, y_top_pos)

    # Position the bottom unit (mirrored vertically)
    inner_unit_bottom_ref = c << inner_link_unit(**inner_unit_params, layer=layer)
    inner_unit_bottom_ref.center = (0, -y_top_pos)

    return c

# Define parameters based on visual inspection for matching the target image
# Footprint is fixed by the prompt
FOOTPRINT_UM = [3.0, 5.5]

# Parameters for the outer elliptical frame
FRAME_THICKNESS = 0.15 # Visually consistent with the image

# Parameters for the inner structures
INNER_VERTICAL_GAP = 0.6 # Gap between the two inner chain-link units

# Parameters for a single inner_link_unit
INNER_UNIT_PARAMETERS = {
    "pad_width": 0.5,
    "pad_length": 0.5,
    "center_bar_width": 0.2,
    "center_bar_length": 0.2,
    "outer_arm_straight_length": 0.1,
    "outer_arm_taper_out_length": 0.2,
    "outer_arm_taper_out_half_width_increase": 0.2, 
    "outer_arm_taper_in_length": 0.2,
    "outer_arm_narrow_point_half_width": 0.05, 
    "outer_arm_tip_length": 0.05,
}

# Create the device
device = custom_device(
    footprint_um=FOOTPRINT_UM,
    frame_thickness=FRAME_THICKNESS,
    inner_vertical_gap=INNER_VERTICAL_GAP,
    inner_unit_params=INNER_UNIT_PARAMETERS
)

# Save the device to a GDS file
device.write_gds("complex_device.gds")

# Print the computed footprint
computed_width = device.xsize
computed_height = device.ysize

print(f"Computed device width: {computed_width:.3f} um")
print(f"Computed device height: {computed_height:.3f} um")
print(f"Expected footprint_um (from previous context, for reference): {FOOTPRINT_UM}")