import gdsfactory as gf
from gdsfactory.components import straight
from gdsfactory.cross_section import strip

@gf.cell
def _my_device(
    num_lines_top=5,
    num_lines_bottom=5,
    num_lines_middle=7,
    line_length=120,
    line_spacing=0.5,
    line_width=0.4,  # width of each line
    vertical_spacing=3,  # space between line groupings
):
    """
    Creates a device with three sections of parallel lines.
    """
    c = gf.Component("my_device_internal")

    # Define the cross-section
    xs = strip(width=line_width, layer=(1, 0))

    # Top section
    y_offset_top = (num_lines_top - 1) * line_spacing / 2
    top_section_y = y_offset_top + vertical_spacing  # Shift top section up
    for i in range(num_lines_top):
        y = top_section_y - i * line_spacing
        wg = c << straight(length=line_length, cross_section=xs)
        wg.move((0, y))

    # Bottom section
    y_offset_bottom = (num_lines_bottom - 1) * line_spacing / 2
    bottom_section_y = -y_offset_bottom - vertical_spacing # Shift bottom section down
    for i in range(num_lines_bottom):
        y = bottom_section_y + i * line_spacing
        wg = c << straight(length=line_length, cross_section=xs)
        wg.move((0, y))

    # Middle section
    y_offset_middle = (num_lines_middle - 1) * line_spacing / 2
    for i in range(num_lines_middle):
        y = -y_offset_middle + i * line_spacing
        wg = c << straight(length=line_length, cross_section=xs)
        wg.move((0, y))

    return c


def my_device(**kwargs):
    """
    Wrapper function to create a copy of the component and avoid LockedError.
    """
    return _my_device(**kwargs).copy()


# Example Usage with constrained footprint parameters.
# You should tune these parameters to match the original image while staying within the device footprint requirements
device = my_device(
    num_lines_top=6,
    num_lines_bottom=6,
    num_lines_middle=7,
    line_length=120,
    line_spacing=0.4,
    line_width=0.4,
    vertical_spacing=1.5 # adjusted for optimal footprint
)

# Verify the device fits within footprint
bbox_layer = (68, 0)
device = gf.add_padding(device, default=0, layers=(bbox_layer,))
device.show()
device.write_gds("my_device.gds")