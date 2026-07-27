import gdsfactory as gf
from gdsfactory.typings import LayerSpec

@gf.cell
def create_device_from_image(layer: LayerSpec = (1, 0)) -> gf.Component:
    """
    Recreates the device geometry from the provided image using GDSFactory.

    The device consists of an outer elliptical shape with two symmetrical
    internal 'E-shaped' white channels cut out.
    """
    c = gf.Component("oval_with_slotted_channels")

    # --- 1. Define the Outer Ellipse (main black component) ---
    # Footprint from constraint: [3.0, 5.5] um
    # x_radius = 3.0 / 2 = 1.5 um
    # y_radius = 5.5 / 2 = 2.75 um
    outer_ellipse = c << gf.components.ellipse(radii=(1.5, 2.75), layer=layer)

    # --- 2. Parameters for the White Channels (negative space to be subtracted) ---
    # Visual estimations from the image, adjusted for smooth parametric design.
    channel_y_center = 1.2  # Vertical offset of the channel's centerline from y=0
    channel_width_straight = 0.5  # Width of the straight parts of the white channel
    slot_width = 0.6  # Horizontal length of each rectangular "slot" opening
    bridge_width = 0.5  # Horizontal length of the black material bridge between slots
    taper_len = 0.4  # Length of the linear taper segment
    taper_width_outer = 1.0  # Width of the channel at the outer end of the taper (before bend)
    bend_radius = 0.8  # Radius of the centerline for the Euler bend
    bend_angle = 75  # Angle of the Euler bend (degrees, for the curved ends)

    # Define cross_sections for paths/components
    # These effectively define the rectangular profile of the "white" cutouts
    xs_straight_channel = gf.cross_section.cross_section(width=channel_width_straight, layer=layer)
    xs_bend_channel = gf.cross_section.cross_section(width=taper_width_outer, layer=layer)


    # --- 3. Construct the TOP white channel (negative space) ---
    # This component will be a boolean OR of its individual parts.
    white_top_channel_comp = gf.Component("white_top_channel_temp")

    # 3.1. Central straight section (replacing rectangle with gf.components.straight)
    # Total horizontal span = slot_width + bridge_width + slot_width
    straight_length = 2 * slot_width + bridge_width
    straight_center_white_ref = white_top_channel_comp << gf.components.straight(
        length=straight_length, cross_section=xs_straight_channel
    )
    # Move the straight component's centerline to the correct y-position.
    # By default, a straight component's 'o1' is at (0,0) and 'o2' at (length,0).
    # To center it horizontally at x=0 and move its centerline to channel_y_center:
    straight_center_white_ref.move((-straight_length / 2, channel_y_center))


    # 3.2. Left Taper
    # Connects the narrower central part to the wider outer curved part.
    # width1=taper_width_outer (wide end), width2=channel_width_straight (narrow end)
    taper_left_white_ref = white_top_channel_comp << gf.components.taper(
        length=taper_len, width1=taper_width_outer, width2=channel_width_straight, layer=layer
    )
    # Connect its narrower end (o2, facing East) to the left port (o1, facing West) of the central straight.
    taper_left_white_ref.connect("o2", straight_center_white_ref.ports["o1"])


    # 3.3. Right Taper
    # width1=channel_width_straight (narrow end), width2=taper_width_outer (wide end)
    taper_right_white_ref = white_top_channel_comp << gf.components.taper(
        length=taper_len, width1=channel_width_straight, width2=taper_width_outer, layer=layer
    )
    # Connect its narrower end (o1, facing West) to the right port (o2, facing East) of the central straight.
    taper_right_white_ref.connect("o1", straight_center_white_ref.ports["o2"])


    # 3.4. Left Bend (Euler bend for the curved end)
    # Connects to the outer port of the left taper (`taper_left_white_ref.ports["o1"]`, which is wide and facing West).
    # `bend_euler` default 'o1' is west-pointing, 'o2' is north-pointing for positive angle. This matches the taper's 'o1'.
    bend_left_white_ref = white_top_channel_comp << gf.components.bend_euler(
        radius=bend_radius, angle=bend_angle, cross_section=xs_bend_channel
    )
    bend_left_white_ref.connect("o1", taper_left_white_ref.ports["o1"])

    # 3.5. Right Bend (Euler bend for the curved end)
    # Connects to the outer port of the right taper (`taper_right_white_ref.ports["o2"]`, which is wide and facing East).
    # Rotate the bend by 180 degrees so its 'o1' port (normally west-facing) now faces east,
    # allowing it to connect to the taper's 'o2' (east-facing).
    bend_right_white_ref = white_top_channel_comp << gf.components.bend_euler(
        radius=bend_radius, angle=bend_angle, cross_section=xs_bend_channel
    )
    bend_right_white_ref.connect("o1", taper_right_white_ref.ports["o2"]).rotate(180)

    # 3.6. Combine all parts of the top white channel using boolean OR
    # This creates a single polygon representing the top cutout.
    combined_parts = gf.boolean(straight_center_white_ref, taper_left_white_ref, "or", layer=layer)
    combined_parts = gf.boolean(combined_parts, taper_right_white_ref, "or", layer=layer)
    combined_parts = gf.boolean(combined_parts, bend_left_white_ref, "or", layer=layer)
    final_white_top_channel = gf.boolean(combined_parts, bend_right_white_ref, "or", layer=layer)

    # 3.7. Create a new component for the final top channel shape for easier mirroring
    # The result of boolean is a Component (or ComponentReference). To mirror easily, let's wrap it.
    top_channel_as_comp = gf.Component("top_channel_final_shape")
    top_channel_as_comp << final_white_top_channel # Add the boolean result as a reference.

    # --- 4. Create the BOTTOM white channel by mirroring the top one ---
    # Mirror across the x-axis (axis from (0,0) to (1,0)).
    white_bottom_channel_comp = top_channel_as_comp.mirror((0, 0), (1, 0))

    # --- 5. Perform boolean subtractions from the outer ellipse ---
    # 5.1. Subtract the top channel
    result_after_top_cut = gf.boolean(outer_ellipse, top_channel_as_comp, operation="not", layer=layer)
    # 5.2. Subtract the bottom channel from the intermediate result
    final_geometry = gf.boolean(result_after_top_cut, white_bottom_channel_comp, operation="not", layer=layer)

    # Add the final geometry (which is a Component from boolean operation) to the main component `c`
    c << final_geometry
    return c

if __name__ == "__main__":
    # Create the device
    device = create_device_from_image()

    # Verify footprint (optional, GDSFactory auto-calculates bounds)
    print(f"Device bounds: {device.dbbox()}")
    # Expected bounds should be close to [-1.5, -2.75, 1.5, 2.75]

    # Display the device (requires KLayout or similar viewer)
    # gf.show(device) # Uncomment to open in KLayout

    # Write to GDS file
    device.write_gds("oval_slotted_device.gds")