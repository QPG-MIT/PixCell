import gdsfactory as gf

# Define a default layer for all geometries
LAYER = (1, 0)

@gf.cell
def make_racetrack(width: float, height: float, layer: tuple = LAYER) -> gf.Component:
    """
    Creates a racetrack (oval) shape by combining a rectangle and two circles.
    Assumes width and height define the total extent of the shape.
    Automatically handles orientation (horizontal or vertical).
    """
    if width <= 0 or height <= 0:
        raise ValueError(f"Width ({width}) and height ({height}) must be positive.")

    # Handle perfect circle case if width and height are effectively equal
    if abs(width - height) < 1e-9:
        return gf.components.circle(radius=width / 2, layer=layer)

    # Create an empty component to place references for boolean operation
    # This component will temporarily hold the parts of the racetrack.
    c_temp_parts = gf.Component("racetrack_boolean_parts_temp") 
    
    # This list will hold the ComponentReferences that we will pass to gf.boolean
    elements_for_boolean = []

    if width > height: # Horizontal racetrack (caps on left/right)
        radius = height / 2
        rect_width = width - height
        
        # Create base components (these are not yet references, so they are not locked)
        rect_base = gf.components.rectangle(size=(rect_width, height), layer=layer, centered=True)
        circle_left_base = gf.components.circle(radius=radius, layer=layer)
        circle_right_base = gf.components.circle(radius=radius, layer=layer)
        
        # Add references to c_temp_parts and transform the references
        rect_ref = c_temp_parts << rect_base
        elements_for_boolean.append(rect_ref)
        
        circle_left_ref = c_temp_parts << circle_left_base
        circle_left_ref.center = (-rect_width / 2 - radius, 0)
        elements_for_boolean.append(circle_left_ref)
        
        circle_right_ref = c_temp_parts << circle_right_base
        circle_right_ref.center = (rect_width / 2 + radius, 0)
        elements_for_boolean.append(circle_right_ref)
            
    else: # Vertical racetrack (caps on top/bottom) - our target image orientation
        radius = width / 2
        rect_height = height - width
        
        # Create base components
        rect_base = gf.components.rectangle(size=(width, rect_height), layer=layer, centered=True)
        circle_bottom_base = gf.components.circle(radius=radius, layer=layer)
        circle_top_base = gf.components.circle(radius=radius, layer=layer)
        
        # Add references to c_temp_parts and transform the references
        rect_ref = c_temp_parts << rect_base
        elements_for_boolean.append(rect_ref)
        
        circle_bottom_ref = c_temp_parts << circle_bottom_base
        circle_bottom_ref.center = (0, -rect_height / 2 - radius)
        elements_for_boolean.append(circle_bottom_ref)
        
        circle_top_ref = c_temp_parts << circle_top_base
        circle_top_ref.center = (0, rect_height / 2 + radius)
        elements_for_boolean.append(circle_top_ref)
    
    # Perform boolean union on the list of positioned references
    # gf.boolean will correctly flatten these references and union their polygons.
    return gf.boolean(elements_for_boolean, operation="or", layer=layer)


@gf.cell
def inner_link_unit(
    pad_width: float = 0.8,
    pad_length: float = 0.55,
    connector_width: float = 0.4,
    connector_length: float = 0.24,
    outer_straight_length: float = 0.08,
    outer_taper_out_length: float = 0.24,
    outer_taper_max_width: float = 4.6, # Full width at the widest point of the outward taper
    outer_taper_in_length: float = 0.24,
    outer_end_width: float = 0.8, # Full width of the final outer straight segment
    outer_end_length: float = 0.08,
    layer: tuple = LAYER
) -> gf.Component:
    """
    Creates one complete inner chain-link-like structure as a single polygon.
    The component is centered at (0,0).

    Args:
        pad_width: Vertical size of the central rectangular "eyes".
        pad_length: Horizontal size of the central rectangular "eyes".
        connector_width: Vertical size of the thin bar connecting the "eyes".
        connector_length: Horizontal size of the thin bar connecting the "eyes".
        outer_straight_length: Straight segment length from eye before first taper.
        outer_taper_out_length: Length of the outward taper.
        outer_taper_max_width: Full width at the widest point of the outward taper.
        outer_taper_in_length: Length of the inward taper.
        outer_end_width: Full width of the final outer straight segment.
        outer_end_length: Length of the final outer straight segment.
        layer: GDS layer for the polygon.
    """
    c = gf.Component("inner_link_unit")

    # Define half-widths for clarity in polygon points calculations
    hw_conn = connector_width / 2
    hw_pad = pad_width / 2
    hw_taper_max = outer_taper_max_width / 2
    hw_final = outer_end_width / 2

    # Define x-coordinates for the right half (from center outwards)
    x_mid_right_conn = connector_length / 2
    x_right_pad_end = x_mid_right_conn + pad_length
    x_right_straight_end = x_right_pad_end + outer_straight_length
    x_right_taper_out_end = x_right_straight_end + outer_taper_out_length
    x_right_taper_in_end = x_right_taper_out_end + outer_taper_in_length
    x_right_final_end = x_right_taper_in_end + outer_end_length

    # Define x-coordinates for the left half (from center outwards, negative)
    x_mid_left_conn = -connector_length / 2
    x_left_pad_end = x_mid_left_conn - pad_length
    x_left_straight_end = x_left_pad_end - outer_straight_length
    x_left_taper_out_end = x_left_straight_end - outer_taper_out_length
    x_left_taper_in_end = x_left_taper_out_end - outer_taper_in_length
    x_left_final_end = x_left_taper_in_end - outer_end_length

    # Polygon points (clockwise order, starting from top-right-most corner)
    points = []

    # 1. Top path of the right half (from rightmost tip towards center)
    points.append((x_right_final_end, hw_final))
    points.append((x_right_taper_in_end, hw_final))
    points.append((x_right_taper_out_end, hw_taper_max))
    points.append((x_right_straight_end, hw_pad))
    points.append((x_right_pad_end, hw_pad))
    points.append((x_mid_right_conn, hw_conn)) # Point where right pad meets central connector

    # 2. Top path of the left half (from center towards leftmost tip)
    points.append((x_mid_left_conn, hw_conn)) # Point where left pad meets central connector
    points.append((x_left_pad_end, hw_pad))
    points.append((x_left_straight_end, hw_pad))
    points.append((x_left_taper_out_end, hw_taper_max))
    points.append((x_left_taper_in_end, hw_final))
    points.append((x_left_final_end, hw_final))

    # 3. Bottom path of the left half (from leftmost tip towards center)
    points.append((x_left_final_end, -hw_final))
    points.append((x_left_taper_in_end, -hw_final))
    points.append((x_left_taper_out_end, -hw_taper_max))
    points.append((x_left_straight_end, -hw_pad))
    points.append((x_left_pad_end, -hw_pad))
    points.append((x_mid_left_conn, -hw_conn)) # Point where left pad meets central connector

    # 4. Bottom path of the right half (from center towards rightmost tip)
    points.append((x_mid_right_conn, -hw_conn)) # Point where right pad meets central connector
    points.append((x_right_pad_end, -hw_pad))
    points.append((x_right_straight_end, -hw_pad))
    points.append((x_right_taper_out_end, -hw_taper_max))
    points.append((x_right_taper_in_end, -hw_final))
    points.append((x_right_final_end, -hw_final))

    c.add_polygon(points, layer=layer)
    return c


@gf.cell
def custom_device(
    footprint_um: list = [3.0, 5.5],
    frame_thickness: float = 0.15,
    inner_vertical_gap: float = 0.6,
    inner_unit_params: dict = None,
    layer: tuple = LAYER
) -> gf.Component:
    """
    Creates the device matching the target image, consisting of an
    oval (racetrack) frame and two inner symmetrical chain-link-like structures.

    Args:
        footprint_um: [width, height] of the overall device.
        frame_thickness: Thickness of the outer oval frame.
        inner_vertical_gap: Vertical gap between the two inner chain-link units.
        inner_unit_params: Dictionary of parameters to pass to `inner_link_unit`.
        layer: GDS layer for all geometries.
    """
    c = gf.Component("complex_device")

    # 1. Outer Oval (Racetrack) Frame using the make_racetrack function
    oval_width = footprint_um[0]
    oval_height = footprint_um[1]

    outer_oval_shape = make_racetrack(width=oval_width, height=oval_height, layer=layer)
    
    # Calculate inner oval dimensions, ensuring they are valid
    inner_oval_width = oval_width - 2 * frame_thickness
    inner_oval_height = oval_height - 2 * frame_thickness

    if inner_oval_width <= 0 or inner_oval_height <= 0:
        raise ValueError(
            f"Inner oval dimensions are zero or negative after subtracting frame thickness. "
            f"Resulting width: {inner_oval_width:.3f}, height: {inner_oval_height:.3f}. "
            "Please reduce frame_thickness or increase footprint_um."
        )

    inner_oval_shape = make_racetrack(width=inner_oval_width, height=inner_oval_height, layer=layer)

    # Use boolean operation to create the hollow frame
    elliptical_frame = gf.boolean(outer_oval_shape, inner_oval_shape, operation="not", layer=layer)
    elliptical_frame_ref = c << elliptical_frame
    elliptical_frame_ref.center = (0,0) # Ensure the frame is centered

    # 2. Inner Chain-Link Structures
    if inner_unit_params is None:
        inner_unit_params = {} # Use default parameters if none are provided

    # Instantiate a temporary unit to get its dimensions for positioning
    temp_unit_for_bounds = inner_link_unit(**inner_unit_params)
    unit_half_height = temp_unit_for_bounds.ysize / 2

    # Position the top inner unit
    y_top_pos = unit_half_height + inner_vertical_gap / 2
    inner_unit_top_ref = c << inner_link_unit(**inner_unit_params, layer=layer)
    inner_unit_top_ref.center = (0, y_top_pos)

    # Position the bottom inner unit (symmetrically below the center)
    inner_unit_bottom_ref = c << inner_link_unit(**inner_unit_params, layer=layer)
    inner_unit_bottom_ref.center = (0, -y_top_pos)

    return c

# Define parameters based on visual inspection and footprint constraint
FOOTPRINT_UM = [3.0, 5.5] # As per constraint

FRAME_THICKNESS = 0.15 # Thickness of the outer oval frame
INNER_VERTICAL_GAP = 0.6 # Vertical gap between the two inner chain-link units

# Parameters for a single inner_link_unit, carefully tuned for visual match and footprint fit
INNER_UNIT_PARAMETERS = {
    "pad_width": 0.8,
    "pad_length": 0.55,
    "connector_width": 0.4,
    "connector_length": 0.24,
    "outer_straight_length": 0.08,
    "outer_taper_out_length": 0.24,
    "outer_taper_max_width": 4.6, # Key parameter to control overall vertical extent of inner unit
    "outer_taper_in_length": 0.24,
    "outer_end_width": 0.8,
    "outer_end_length": 0.08,
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

# Print the computed footprint for verification
computed_width = device.xsize
computed_height = device.ysize

print(f"Computed device width: {computed_width:.3f} um")
print(f"Computed device height: {computed_height:.3f} um")
print(f"Expected footprint_um: {FOOTPRINT_UM}")