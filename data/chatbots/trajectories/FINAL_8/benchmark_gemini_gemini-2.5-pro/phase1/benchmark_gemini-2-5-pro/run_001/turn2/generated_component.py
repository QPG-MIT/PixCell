import gdsfactory as gf
from gdsfactory.cross_section import Section, CrossSection

@gf.cell
def create_device():
    """
    Creates the device shown in the image by assembling three parametric components:
    a central bundle of straight lines, and top and bottom U-shaped multi-line jaws.
    """
    # 1. Define parameters based on footprint and visual analysis
    footprint_width = 120.0
    footprint_height = 4.0
    num_lines_per_section = 5
    layer = (1, 0)

    # The total vertical height is composed of 3 sections of lines and 2 gaps.
    # Assuming line_width = gap_width = w:
    # 4.0 = 3 * (5*w + 4*w) + 2*w = 3 * 9w + 2w = 27w + 2w = 29w
    w = footprint_height / 29.0
    g = w
    
    # Create the main component to hold the final assembly
    c = gf.Component("main_device")

    # 2. Create the central bundle of straight lines
    section_height = num_lines_per_section * w + (num_lines_per_section - 1) * g
    pitch = w + g
    y_start = -section_height / 2 + w / 2

    # Define the cross_section and create the straight primitive component ONCE for efficiency
    xs_straight = gf.cross_section.cross_section(width=w, layer=layer)
    straight_primitive = gf.components.straight(length=footprint_width, cross_section=xs_straight)

    # Add multiple references of the primitive directly to the main component 'c'
    for i in range(num_lines_per_section):
        y_pos = y_start + i * pitch
        s_ref = c.add_ref(straight_primitive)
        # FIX: The .move() method takes a tuple (dx, dy) for relative moves.
        # The 'destination=' keyword was causing the error.
        s_ref.move((-footprint_width / 2, y_pos))

    # 3. Create the U-shaped "jaw" template component
    bend_radius = 5.0
    straight_length = footprint_width - 2 * bend_radius

    # Define the U-shaped path
    path = gf.Path()
    path.append(gf.path.euler(radius=bend_radius, angle=-90))
    path.append(gf.path.straight(length=straight_length))
    path.append(gf.path.euler(radius=bend_radius, angle=90))

    # Define the custom multi-line cross-section for the jaws
    center_offset_index = (num_lines_per_section - 1) / 2
    offsets = [(i - center_offset_index) * pitch for i in range(num_lines_per_section)]
    sections = [Section(width=w, offset=offset, layer=layer) for offset in offsets]
    xs_multi = CrossSection(sections=sections)

    # Extrude the path to create the jaw component
    c_jaw = gf.path.extrude(path, cross_section=xs_multi)

    # 4. Assemble the final device by adding and positioning the jaws
    y_jaw_center = section_height + g

    # Add and position the top jaw
    jaw_top_ref = c.add_ref(c_jaw)
    # FIX: Corrected the .move() call here as well.
    jaw_top_ref.move((-footprint_width / 2, y_jaw_center))

    # Add, mirror, and position the bottom jaw
    jaw_bottom_ref = c.add_ref(c_jaw)
    jaw_bottom_ref.mirror(p1=(0, 0), p2=(1, 0)) # Mirror across the x-axis
    # FIX: Corrected the .move() call for the final component.
    jaw_bottom_ref.move((-footprint_width / 2, -y_jaw_center))

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