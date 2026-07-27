import gdsfactory as gf

@gf.cell
def arrow_cross():
    """
    Creates an arrow-shaped cross device with four arms pointing inwards.
    Each arm consists of a tapered section and a straight stem,
    combined using boolean operations.
    """
    c = gf.Component()
    layer = (1, 0)

    # --- Parameters derived from the footprint and visual analysis ---
    total_device_size = 4.7  # Total width/height of the device
    half_device_size = total_device_size / 2  # Distance from center to tip of an arm (2.35 um)

    stem_width = 0.6  # Width of the narrowest part of the arm (outer stem)
    stem_length = 0.8  # Length of the outer straight stem

    arrow_max_width = 1.8 # The widest part of the arrow, where it meets the central cross.
                          # This width defines the central square part of the cross.

    # The length of the tapered section of the arm.
    # It starts from the center (where width is arrow_max_width)
    # and ends where it connects to the straight stem (where width is stem_width).
    taper_length_from_center = half_device_size - stem_length # 2.35 - 0.8 = 1.55 um

    # --- 1. Construct one "arrow arm" template pointing to the right ---
    # This arm starts at the device's center (x=0) with the maximum arrow width,
    # tapers down to the stem width, and then continues as a straight stem.
    one_arm_builder = gf.Component("one_arrow_arm_template")

    # a. Tapered part of the arm (arrow head)
    # This taper starts at x=0 (the center of the cross) with width `arrow_max_width`,
    # and linearly reduces its width to `stem_width` over `taper_length_from_center`.
    # `gf.components.taper` is vertically centered (around Y=0) by default, and starts at X=0.
    taper_segment = one_arm_builder << gf.components.taper(
        length=taper_length_from_center,
        width1=arrow_max_width, # Wide end (at cross center)
        width2=stem_width,     # Narrow end (connecting to the stem)
        layer=layer,
    )

    # b. Outer straight stem part
    # Create the rectangle centered initially at its own (0,0).
    stem_rect = one_arm_builder << gf.components.rectangle(
        size=(stem_length, stem_width), layer=layer, centered=True
    )
    # Move the stem_rect so its left edge (when centered at (0,0))
    # aligns with the end of the taper.
    # The taper ends at x = taper_length_from_center.
    # The stem's center needs to be at taper_length_from_center + stem_length / 2.
    stem_rect.movex(taper_length_from_center + stem_length / 2)

    # Combine these two parts (taper and stem) into a single reusable Component.
    # This `right_arm_shape_template` extends from x=0 (center) to x=half_device_size (tip),
    # and is centered vertically on y=0.
    right_arm_shape_template = gf.boolean(
        taper_segment, stem_rect, operation="or", layer=layer
    )

    # --- 2. Assemble the full cross using the arm template and boolean operations ---
    # Start the combined geometry with the first arm (right-pointing).
    # Its origin (x=0, y=0) is at the center of the final device.
    combined_geometry = right_arm_shape_template

    # Add and boolean other arms by rotating the template
    # Each `gf.boolean` operation creates a new Component with the combined geometry.

    # Up arm (rotate 90 degrees around the origin)
    up_arm = right_arm_shape_template.copy().rotate(90)
    combined_geometry = gf.boolean(combined_geometry, up_arm, "or", layer=layer)

    # Left arm (rotate 180 degrees around the origin)
    left_arm = right_arm_shape_template.copy().rotate(180)
    combined_geometry = gf.boolean(combined_geometry, left_arm, "or", layer=layer)

    # Down arm (rotate 270 degrees around the origin)
    down_arm = right_arm_shape_template.copy().rotate(270)
    combined_geometry = gf.boolean(combined_geometry, down_arm, "or", layer=layer)

    # Add the final combined geometry (which is now a Component) to the main component `c`.
    # This ensures the entire cross shape is contained within the returned component.
    c.add_ref(combined_geometry)

    return c

# Create and save the GDS device
if __name__ == "__main__":
    device = arrow_cross()
    device.write_gds("arrow_cross.gds")
    device.show() # Optional: display the component