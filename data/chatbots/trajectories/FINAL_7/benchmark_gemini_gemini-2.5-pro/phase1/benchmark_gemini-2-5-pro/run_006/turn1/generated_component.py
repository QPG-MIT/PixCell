import gdsfactory as gf

def _create_stadium_from_primitives(length: float, radius: float, layer: tuple) -> gf.Component:
    """
    Creates a stadium shape (rectangle with semicircular ends) by combining
    a central rectangle and two circles using a boolean union.
    
    Args:
        length: The length of the central straight section.
        radius: The radius of the semicircular ends.
        layer: The GDS layer for the shape.
        
    Returns:
        A GDSFactory Component representing the stadium shape.
    """
    c = gf.Component()
    
    # Create the central rectangular part
    rect = gf.components.rectangle(size=(length, 2 * radius), layer=layer, centered=True)
    
    # Create the two circular end caps
    circle_left = gf.components.circle(radius=radius, layer=layer)
    circle_right = gf.components.circle(radius=radius, layer=layer)
    
    # Position the circles at the ends of the rectangle's centerline
    circle_left.movex(-length / 2)
    circle_right.movex(length / 2)
    
    # Union all the parts into a single shape
    stadium = gf.boolean(A=rect, B=[circle_left, circle_right], operation="or", layer=layer)
    
    # Add a reference to the final shape in the component
    c << stadium
    return c


@gf.cell
def create_device():
    """
    Recreates the specified device geometry using GDSFactory's parametric
    primitives and boolean operations, adhering to the provided footprint.

    The construction follows a three-step process:
    1. Create a hollow outer stadium-shaped ring using a custom helper function.
    2. Create a template for the inner horizontal 'ladder' bars.
    3. Assemble the ring and two instances of the bars, uniting them
       into a single, clean geometry.
    """

    # --- 1. Define Dimensions ---
    footprint_width = 5.5
    footprint_height = 3.0
    ring_width = 0.5
    bar_height = 0.7
    central_gap = 0.6
    hole_height = 0.3
    hole_width = 0.8
    strut_width = 0.3
    layer = (1, 0)

    # Derived dimensions for clarity and parametricity
    outer_radius = footprint_height / 2
    outer_length = footprint_width - 2 * outer_radius

    inner_radius = outer_radius - ring_width
    inner_length = footprint_width - 2 * ring_width - 2 * inner_radius
    
    bar_length = inner_length
    bar_y_offset = central_gap / 2 + bar_height / 2
    hole_spacing = hole_width + strut_width

    # --- 2. Create Geometric Parts ---

    # Part A: The hollow outer ring (stadium shape)
    # CORRECTED: Use the custom helper function to build stadiums from primitives.
    outer_stadium = _create_stadium_from_primitives(
        length=outer_length, radius=outer_radius, layer=layer
    )
    inner_stadium = _create_stadium_from_primitives(
        length=inner_length, radius=inner_radius, layer=layer
    )
    ring = gf.boolean(A=outer_stadium, B=inner_stadium, operation="not", layer=layer)

    # Part B: A template for the central bars with two holes
    bar_body = gf.components.rectangle(size=(bar_length, bar_height), layer=layer)
    hole_primitive = gf.components.rectangle(
        size=(hole_width, hole_height), layer=layer
    )
    
    hole1 = hole_primitive.copy().move((-hole_spacing / 2, 0))
    hole2 = hole_primitive.copy().move((hole_spacing / 2, 0))
    
    bar_with_holes = gf.boolean(A=bar_body, B=[hole1, hole2], operation="not", layer=layer)

    # --- 3. Assemble and Union the Final Device ---
    
    top_bar = bar_with_holes.copy().movey(bar_y_offset)
    bottom_bar = bar_with_holes.copy().movey(-bar_y_offset)

    final_device = gf.boolean(A=ring, B=[top_bar, bottom_bar], operation="or", layer=layer)
    
    return final_device

# --- Main execution block for visualization and verification ---
if __name__ == "__main__":
    device = create_device()
    device.show()
    
    print(f"Device size (width, height): {device.size}")
    print(f"Footprint constraint (width, height): ({5.5}, {3.0})")