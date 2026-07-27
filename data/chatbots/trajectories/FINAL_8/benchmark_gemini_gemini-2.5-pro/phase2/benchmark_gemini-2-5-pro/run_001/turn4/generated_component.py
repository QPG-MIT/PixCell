import gdsfactory as gf
from gdsfactory.cross_section import Section, CrossSection

@gf.cell
def create_device():
    """
    Creates the device matching the target image.

    This version corrects a TypeError from the previous attempt. The function
    `gf.components.coupler_straight` does not accept an 'N' argument to create
    N parallel waveguides; it is designed for two-waveguide couplers only.

    Correction:
    - Reverted the creation of the central bundle to use a `for` loop, which
      is the correct and flexible method for creating an array of N straight
      waveguides. The incorrect `coupler_straight` call has been removed.
    """
    # 1. Define parameters with adjusted width for better rendering.
    device_width = 12.0
    device_height = 4.0
    num_lines = 5
    layer = (1, 0)
    bend_radius_outer = 2.0

    # 2. Calculate fundamental vertical dimensions (width, gap, pitch).
    w = device_height / 29.0
    g = w
    pitch = w + g

    # Create the main component for the final assembly.
    c = gf.Component("main_device_v6")
    xs_single = gf.cross_section.cross_section(width=w, layer=layer)

    # 3. Create the central bundle of straight lines using a for loop.
    # This is the correct method for creating N > 2 parallel waveguides.
    central_bundle = gf.Component("central_bundle")
    bundle_height = num_lines * w + (num_lines - 1) * g
    y_start = -bundle_height / 2 + w / 2
    for i in range(num_lines):
        s = gf.components.straight(length=device_width, cross_section=xs_single)
        s_ref = central_bundle << s
        s_ref.y = y_start + i * pitch
        
    central_ref = c << central_bundle
    central_ref.center = (0, 0)

    # 4. Create the U-shaped jaw components.

    # TOP JAW (opens upwards)
    c_jaw_top = gf.Component("jaw_top")
    for i in range(num_lines):
        r_i = bend_radius_outer - i * pitch
        straight_len_i = device_width - 2 * r_i
        if straight_len_i <= 0:
            continue

        path = gf.Path()
        path.append(gf.path.euler(radius=r_i, angle=90))
        path.append(gf.path.straight(length=straight_len_i))
        path.append(gf.path.euler(radius=r_i, angle=-90))

        line = path.extrude(cross_section=xs_single)
        line_ref = c_jaw_top << line
        line_ref.move(origin=(0, 0), destination=(-device_width / 2, i * pitch))

    # BOTTOM JAW (opens downwards)
    c_jaw_bottom = gf.Component("jaw_bottom")
    for i in range(num_lines):
        r_i = bend_radius_outer - i * pitch
        straight_len_i = device_width - 2 * r_i
        if straight_len_i <= 0:
            continue
        
        path = gf.Path()
        path.append(gf.path.euler(radius=r_i, angle=-90))
        path.append(gf.path.straight(length=straight_len_i))
        path.append(gf.path.euler(radius=r_i, angle=90))

        line = path.extrude(cross_section=xs_single)
        line_ref = c_jaw_bottom << line
        line_ref.move(origin=(0, 0), destination=(-device_width / 2, -i * pitch))

    # 5. Assemble the final device using robust relative positioning.
    gap_between_sections = g

    jaw_top_ref = c << c_jaw_top
    jaw_top_ref.x = central_ref.x
    jaw_top_ref.ymin = central_ref.ymax + gap_between_sections

    jaw_bottom_ref = c << c_jaw_bottom
    jaw_bottom_ref.x = central_ref.x
    jaw_bottom_ref.ymax = central_ref.ymin - gap_between_sections

    return c

# This block ensures the following code only runs when the script is executed directly
if __name__ == "__main__":
    # Instantiate the component
    device = create_device()
    
    # Write the component to a GDS file named "device.gds"
    device.write_gds("device.gds")

    # (Optional) Show the component in a viewer like KLayout
    print("GDS file 'device.gds' written successfully.")
    device.show()