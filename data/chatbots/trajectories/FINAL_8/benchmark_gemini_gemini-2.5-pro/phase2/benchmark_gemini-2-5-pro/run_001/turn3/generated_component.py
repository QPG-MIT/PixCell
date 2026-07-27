import gdsfactory as gf
from gdsfactory.cross_section import Section, CrossSection

@gf.cell
def create_device():
    """
    Creates the device shown in the image.

    This version corrects the jaw generation by creating a unique path for each
    of the 5 lines in the U-bend. It also fixes the reference positioning method
    to use the robust .move(origin, destination) call to resolve the TypeError.
    """
    # 1. Define parameters based on footprint and visual analysis
    footprint_width = 120.0
    footprint_height = 4.0
    num_lines = 5
    layer = (1, 0)
    # Define the radius for the outermost line of the U-shaped jaw
    bend_radius_outer = 5.0

    # 2. Calculate fundamental dimensions (width, gap, pitch)
    # The total vertical height is composed of 3 sections of lines and 2 gaps.
    # Assuming the line width and all gaps are equal (w):
    # Total Height = 3 * section_height + 2 * gap_between_sections
    # section_height = 5*w + 4*w = 9w
    # Total Height = 3 * 9w + 2*w = 27w + 2w = 29w
    w = footprint_height / 29.0
    g = w
    pitch = w + g  # Pitch between adjacent lines within a section

    # Create the main component to hold the final assembly
    c = gf.Component("main_device")

    # 3. Create the central bundle of straight lines
    xs_single = gf.cross_section.cross_section(width=w, layer=layer)
    section_height = num_lines * w + (num_lines - 1) * g
    y_start = -section_height / 2 + w / 2

    for i in range(num_lines):
        s_ref = c << gf.components.straight(length=footprint_width, cross_section=xs_single)
        # FIX: The .move() method requires both 'origin' and 'destination'.
        # The straight component is centered at (0, 0) by default, which is our origin.
        s_ref.move(origin=(0, 0), destination=(0, y_start + i * pitch))

    # 4. Create the U-shaped "jaw" component by building it line-by-line
    c_jaw = gf.Component("jaw")

    for i in range(num_lines):
        r_i = bend_radius_outer - i * pitch
        straight_len_i = footprint_width - 2 * r_i

        path = gf.Path()
        path.append(gf.path.euler(radius=r_i, angle=-90))
        path.append(gf.path.straight(length=straight_len_i))
        path.append(gf.path.euler(radius=r_i, angle=90))

        line = path.extrude(cross_section=xs_single)
        line_ref = c_jaw << line
        
        # FIX: The extruded component's origin is at the start of the path (0, 0).
        # We move this origin to its final position within the jaw sub-component.
        line_ref.move(origin=(0, 0), destination=(-footprint_width / 2, i * pitch))

    # 5. Assemble the final device by adding and positioning the jaws
    y_jaw_offset = (section_height / 2) + g + (w / 2)

    # Add and position the top jaw
    jaw_top_ref = c << c_jaw
    # FIX: Move the jaw component's origin (0,0) to its final y-offset.
    jaw_top_ref.move(origin=(0, 0), destination=(0, y_jaw_offset))

    # Add, mirror, and position the bottom jaw
    jaw_bottom_ref = c << c_jaw
    jaw_bottom_ref.mirror()
    # FIX: Move the mirrored jaw's origin to the negative y-offset.
    jaw_bottom_ref.move(origin=(0, 0), destination=(0, -y_jaw_offset))

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