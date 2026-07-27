import gdsfactory as gf
import numpy as np

@gf.cell
def create_top_oriented_bracket_block(
    length: float = 120.0,
    total_block_height: float = 1.35, # Expected height (5*lw + 4*gw) for lines and gaps
    line_width: float = 0.15,
    gap_width: float = 0.15,
    R_curve: float = 1.0, # Radius for the rounded corners
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Creates a bracket-like block with internal parallel lines.
    This component is 'top-oriented': rounded at the top corners and flat at the bottom.
    Its ymin will be 0 and ymax will be total_block_height.
    """
    c = gf.Component()

    # Calculate the height of the rectangular part of the outer envelope.
    # The circles will extend R_curve above this rectangle's top edge.
    straight_rect_height = total_block_height - R_curve

    # Create a temporary component to build the solid outer shape.
    # This component will contain references to primitives, which can be transformed.
    outer_solid_shape_container = gf.Component("outer_solid_shape_container")

    # 1. Add references to the container and position them to form the solid outer envelope.
    
    # Main rectangle reference
    rect_ref = outer_solid_shape_container << gf.components.rectangle(
        size=(length, straight_rect_height),
        layer=layer,
        centered=False # Important for predictable placement from (0,0)
    )
    rect_ref.xmin = 0
    rect_ref.ymin = 0 # Position the bottom edge of the rectangle at y=0

    # Circle references for the rounded top-left and top-right corners.
    circle_left_ref = outer_solid_shape_container << gf.components.circle(radius=R_curve, layer=layer)
    circle_right_ref = outer_solid_shape_container << gf.components.circle(radius=R_curve, layer=layer)

    # Position circle centers such that their lowest point of curvature aligns
    # with the top edge of the main rectangle.
    circle_left_ref.center = (R_curve, straight_rect_height)
    circle_right_ref.center = (length - R_curve, straight_rect_height)

    # Now, outer_solid_shape_container holds the desired solid shape geometry
    # via its transformed references.

    # 2. Create a temporary component to hold the internal gaps (rectangular shapes to be subtracted).
    gaps_container = gf.Component("gaps_for_bracket_container")
    for i in range(4):
        gap_rect_ref = gaps_container << gf.components.rectangle( # Add reference to gaps_container
            size=(length, gap_width),
            layer=layer,
            centered=False
        )
        gap_rect_ref.xmin = 0
        # Gaps are positioned starting from the bottom of the block,
        # accounting for line_width and gap_width.
        gap_rect_ref.ymin = (i + 1) * line_width + i * gap_width

    # 3. Perform boolean subtraction using the geometry from the temporary containers.
    # gf.boolean will take the geometry represented by these components.
    final_patterned_block = gf.boolean(
        outer_solid_shape_container, gaps_container, operation="not", layer=layer
    )
    
    # Add the final result to the main component 'c' that will be returned.
    c << final_patterned_block

    return c

@gf.cell
def create_central_lines(
    length: float = 120.0,
    line_width: float = 0.15,
    gap_width: float = 0.15,
    n_lines: int = 4, # The central part has 4 lines
    layer: tuple = (1, 0)
) -> gf.Component:
    """Creates a set of parallel straight lines."""
    c = gf.Component("central_lines")
    for i in range(n_lines):
        # 'line' here is a ComponentReference, so transforming its xmin/ymin is valid.
        line = c << gf.components.rectangle(
            size=(length, line_width),
            layer=layer,
            centered=False # Ensure bottom-left is at (0,0) before moving
        )
        line.xmin = 0
        line.ymin = i * (line_width + gap_width)
    return c

@gf.cell
def full_device(
    device_length: float = 120.0,
    device_height: float = 4.0,
    line_width: float = 0.15,
    gap_width: float = 0.15,
    R_curve: float = 1.0,
    layer: tuple = (1, 0)
) -> gf.Component:
    """
    Assembles the full device: top bracket, bottom bracket, and central lines.
    Ensures all components fit within the specified device_length and device_height.
    """
    c = gf.Component("full_device")

    # Define dimensions for the top/bottom bracket blocks.
    n_bracket_lines = 5
    total_bracket_height = (n_bracket_lines * line_width) + ((n_bracket_lines - 1) * gap_width)

    # 1. Create and position the top bracket block.
    top_block_comp = create_top_oriented_bracket_block(
        length=device_length,
        total_block_height=total_bracket_height,
        line_width=line_width,
        gap_width=gap_width,
        R_curve=R_curve,
        layer=layer
    )
    top_block_ref = c << top_block_comp
    # The top_block_comp has ymin=0 and ymax=total_bracket_height.
    # We want its ymax to be at the device's top edge (device_height).
    top_block_ref.ymax = device_height
    top_block_ref.xmin = 0 # Align to the left edge of the device.

    # 2. Create and position the bottom bracket block.
    # Start by creating a top-oriented block.
    bottom_block_comp_base = create_top_oriented_bracket_block(
        length=device_length,
        total_block_height=total_bracket_height,
        line_width=line_width,
        gap_width=gap_width,
        R_curve=R_curve,
        layer=layer
    )
    bottom_block_ref = c << bottom_block_comp_base
    # Mirror it around its horizontal center to make it bottom-oriented.
    # (p1 and p2 define the mirroring axis: a line from (0, Y_center) to (length, Y_center))
    bottom_block_ref.mirror(p1=(0, total_bracket_height / 2), p2=(device_length, total_bracket_height / 2))
    # Position the mirrored block at the bottom edge of the device.
    bottom_block_ref.ymin = 0
    bottom_block_ref.xmin = 0 # Align to the left edge of the device.

    # 3. Create and position the central lines component.
    n_center_lines = 4
    center_lines_comp = create_central_lines(
        length=device_length,
        line_width=line_width,
        gap_width=gap_width,
        n_lines=n_center_lines,
        layer=layer
    )
    center_lines_ref = c << center_lines_comp

    # Calculate the total height of the central_lines_comp when its ymin=0.
    height_of_center_lines_comp = (n_center_lines * line_width) + ((n_center_lines - 1) * gap_width)
    
    # Determine the vertical space available between the two bracket blocks.
    available_space_ymin = bottom_block_ref.ymax
    available_space_ymax = top_block_ref.ymin
    
    # Calculate the y-coordinate of the center of this available space.
    y_center_available_space = (available_space_ymin + available_space_ymax) / 2

    # Center the central lines component within this available space.
    center_lines_ref.center = (device_length / 2, y_center_available_space)
    
    return c

if __name__ == "__main__":
    # Define the device footprint.
    FOOTPRINT_LENGTH = 120.0
    FOOTPRINT_HEIGHT = 4.0

    # Define common parameters for the pattern.
    LINE_WIDTH = 0.15
    GAP_WIDTH = 0.15
    R_CURVE = 1.0 # Radius for the rounded corners of the bracket blocks

    # Generate the full device.
    device = full_device(
        device_length=FOOTPRINT_LENGTH,
        device_height=FOOTPRINT_HEIGHT,
        line_width=LINE_WIDTH,
        gap_width=GAP_WIDTH,
        R_curve=R_CURVE
    )
    
    # Show the device in the GDSFactory viewer (requires KLayout or similar).
    device.show()
    
    # You can also save the device to a GDSII file.
    # device.write_gds("pattern_recreation.gds")