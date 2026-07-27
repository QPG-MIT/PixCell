import gdsfactory as gf

@gf.cell
def stylized_cross():
    """
    Creates a stylized cross shape with flared arms and narrow stems.
    The design is based on combining tapers and rectangles, then using boolean operations.
    """
    c = gf.Component()
    layer = (1, 0)

    # --- Parameters derived from the footprint and visual analysis ---
    total_size = 4.7  # Total width/height of the device
    half_size = total_size / 2  # Distance from center to tip of an arm

    stem_width = 0.5  # Width of the narrow stem part and central connection
    stem_length = 0.8  # Length of the narrow stem part

    petal_max_width = 1.3  # Maximum width of the flared/bulbous part of the arm
    # Length of the flared part, from center to where the straight stem begins
    petal_body_length = half_size - stem_length  # 2.35 - 0.8 = 1.55 um

    # --- 1. Create a single "arm segment" that points to the right ---
    # This segment consists of a taper (flared part) and a rectangle (stem part).
    arm_segment_template = gf.Component("arm_segment_template")

    # Tapering part: from narrow (at center) to wide (at petal_max_width)
    # gf.components.taper is always centered vertically around y=0 by default.
    # It extends from x=0 to x=length.
    taper_to_flare = arm_segment_template << gf.components.taper(
        length=petal_body_length,
        width1=stem_width,
        width2=petal_max_width,
        layer=layer,
        # The 'centered' argument is not supported by gf.components.taper.
        # It defaults to being centered vertically around y=0 and starting at x=0.
    )

    # Straight stem part: attaches to the wider end of the taper
    # Create the rectangle centered initially.
    stem_rect = arm_segment_template << gf.components.rectangle(
        size=(stem_length, stem_width),
        layer=layer,
        centered=True  # This rectangle is centered around its own local (0,0)
    )
    # Move the stem_rect to attach its left edge to the end of the taper.
    # The taper ends at x = petal_body_length.
    # The stem_rect's left edge (when centered at (0,0)) is at x = -stem_length/2.
    # To move this left edge to petal_body_length, we move the center by
    # petal_body_length + stem_length/2.
    stem_rect.movex(petal_body_length + stem_length / 2)

    # Boolean OR the taper and the stem_rect to form a single continuous arm segment.
    # This result (right_arm_shape) will be a component that is centered on y=0 and
    # extends from x=0 to x=half_size.
    right_arm_shape = gf.boolean(taper_to_flare, stem_rect, operation="or", layer=layer)

    # --- 2. Create the central connection square ---
    # This ensures a solid connection in the very center where all arms meet.
    # Its size matches the `stem_width` to connect smoothly with the arms.
    central_sq = gf.components.rectangle(
        size=(stem_width, stem_width),
        layer=layer,
        centered=True
    )
    # Start the final geometry with the central square.
    final_device = central_sq

    # --- 3. Add and rotate the four arm segments ---
    # Each 'right_arm_shape' component, when instantiated, is positioned such that
    # its leftmost point is at (0,0) and it extends along the positive X axis,
    # centered vertically around Y=0.
    # When rotated, its central point (the implicit pivot for rotation, (0,0))
    # remains at the global (0,0).
    # The boolean operation `gf.boolean` takes component references or components
    # and merges their geometries based on their current positions/rotations.

    # Right arm (0 degrees rotation)
    right_arm_ref = c << right_arm_shape
    final_device = gf.boolean(final_device, right_arm_ref, "or", layer=layer)

    # Up arm (90 degrees rotation)
    up_arm_ref = c << right_arm_shape.copy().rotate(90)
    final_device = gf.boolean(final_device, up_arm_ref, "or", layer=layer)

    # Left arm (180 degrees rotation)
    left_arm_ref = c << right_arm_shape.copy().rotate(180)
    final_device = gf.boolean(final_device, left_arm_ref, "or", layer=layer)

    # Down arm (270 degrees rotation)
    down_arm_ref = c << right_arm_shape.copy().rotate(270)
    final_device = gf.boolean(final_device, down_arm_ref, "or", layer=layer)

    # Add the final combined shape to the main component 'c'.
    # This ensures the boolean result is part of the returned component.
    c.add_ref(final_device)

    return c

# Create and save the GDS device
if __name__ == "__main__":
    device = stylized_cross()
    device.write_gds("stylized_cross.gds")
    device.show() # Optional: display the component