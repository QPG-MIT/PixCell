import gdsfactory as gf

@gf.cell
def custom_cross_shape(
    x_radius_leaf: float = 0.5, # Half-width of the elliptical leaf at its widest point (center)
    y_radius_leaf: float = 2.0, # Half-length of the elliptical leaf (from center to where it meets stub)
    stub_width: float = 0.3,    # Width of the rectangular stub
    stub_length: float = 0.35,  # Length of the rectangular stub
    layer: tuple = (1, 0),
) -> gf.Component:
    """
    Recreates a cross-like shape with rounded ends and rectangular stubs.

    The shape consists of four overlapping elliptical 'leaves' forming the central
    rounded cross, and four rectangular 'stubs' extending from the tips of these leaves.
    The total extent of the component along X and Y axes will be
    2 * (y_radius_leaf + stub_length).

    Args:
        x_radius_leaf: Semi-minor axis (half-width) of the elliptical leaves.
        y_radius_leaf: Semi-major axis (half-length) of the elliptical leaves
                       (from the center of the cross to the start of the stub).
        stub_width: Width of the rectangular stubs.
        stub_length: Length of the rectangular stubs.
        layer: GDS layer for the component.

    Returns:
        A gdsfactory Component object representing the custom cross shape.
    """

    # 1. Create the four elliptical 'leaves' as distinct Component objects, each rotated.
    # We use gf.copy() to ensure each leaf is an independent component that can be
    # rotated without affecting others, then add them as references to a temporary component.
    # Finally, boolean all these together to form the central body.

    # Start with an initial upright leaf as the base for boolean operations
    leaf_up = gf.components.ellipse(radii=(x_radius_leaf, y_radius_leaf), layer=layer)
    combined_body = leaf_up.to_component() # Ensure it's a standalone Component

    # Create the other three rotated leaves as distinct Components and union them
    leaf_right = gf.components.ellipse(radii=(x_radius_leaf, y_radius_leaf), layer=layer).rotate(90)
    combined_body = gf.boolean(combined_body, leaf_right, operation="or", layer=layer)

    leaf_down = gf.components.ellipse(radii=(x_radius_leaf, y_radius_leaf), layer=layer).rotate(180)
    combined_body = gf.boolean(combined_body, leaf_down, operation="or", layer=layer)

    leaf_left = gf.components.ellipse(radii=(x_radius_leaf, y_radius_leaf), layer=layer).rotate(270)
    combined_body = gf.boolean(combined_body, leaf_left, operation="or", layer=layer)

    # 2. Create and place the four rectangular stubs.
    # Each stub is created as a distinct Component, then rotated and moved.
    stub_template = gf.components.rectangle(size=(stub_width, stub_length), layer=layer, centered=True)

    # Calculate the Y-offset for the stubs.
    # The top of an upward-pointing leaf (centered at 0,0) is at y_radius_leaf.
    # The stub's bottom edge needs to align with this, so its center should be
    # at y_radius_leaf + stub_length / 2.
    stub_offset_from_center = y_radius_leaf + stub_length / 2

    # Create distinct stub components, rotate, and move them.
    stub_up = stub_template.to_component().move((0, stub_offset_from_center))
    stub_right = stub_template.to_component().rotate(90).move((stub_offset_from_center, 0))
    stub_down = stub_template.to_component().rotate(180).move((0, -stub_offset_from_center))
    stub_left = stub_template.to_component().rotate(270).move((-stub_offset_from_center, 0))

    # 3. Combine the central rounded body with all four stubs using boolean OR.
    final_shape = gf.boolean(combined_body, stub_up, operation="or", layer=layer)
    final_shape = gf.boolean(final_shape, stub_right, operation="or", layer=layer)
    final_shape = gf.boolean(final_shape, stub_down, operation="or", layer=layer)
    final_shape = gf.boolean(final_shape, stub_left, operation="or", layer=layer)

    # The footprint constraint is [4.7, 4.7].
    # With y_radius_leaf = 2.0 and stub_length = 0.35, the total half-length
    # from center to tip is 2.0 + 0.35 = 2.35.
    # The full length is 2 * 2.35 = 4.7, which matches the constraint.

    return final_shape

if __name__ == "__main__":
    # Create the component using the specified parameters
    device = custom_cross_shape(
        x_radius_leaf=0.5,
        y_radius_leaf=2.0,
        stub_width=0.3,
        stub_length=0.35,
        layer=(1, 0)
    )

    # Validate the footprint of the generated device
    bbox = device.bbox
    width = bbox[1][0] - bbox[0][0]
    height = bbox[1][1] - bbox[0][1]
    print(f"Device Bounding Box: {bbox}")
    print(f"Device Footprint: [{width:.1f}, {height:.1f}] um")

    # The expected footprint is [4.7, 4.7]
    expected_footprint = (4.7, 4.7)
    assert abs(width - expected_footprint[0]) < 1e-9, f"Width mismatch: {width} vs {expected_footprint[0]}"
    assert abs(height - expected_footprint[1]) < 1e-9, f"Height mismatch: {height} vs {expected_footprint[1]}"
    print("Footprint matches the constraint.")

    # Write the GDS file and show the component (requires KLayout installed)
    device.write_gds("custom_cross_shape.gds")
    device.show()