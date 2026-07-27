import gdsfactory as gf
from gdsfactory.components import straight
from gdsfactory.cross_section import strip

@gf.cell
def _my_device(num_lines_top=5, num_lines_bottom=5, num_lines_middle=3, line_length=120, line_spacing=0.5):
    c = gf.Component("my_device_internal")

    # Define the cross-section
    xs = strip(width=0.4, layer=(1, 0))

    # Top section
    y_offset_top = (num_lines_top - 1) * line_spacing / 2  # Center the lines
    for i in range(num_lines_top):
        y = y_offset_top - i * line_spacing
        wg = c << straight(length=line_length, cross_section=xs)
        wg.move((0, y))

    # Bottom section
    y_offset_bottom = (num_lines_bottom - 1) * line_spacing / 2
    for i in range(num_lines_bottom):
        y = -y_offset_bottom + i * line_spacing
        wg = c << straight(length=line_length, cross_section=xs)
        wg.move((0, y))

    # Middle section
    y_offset_middle = (num_lines_middle - 1) * line_spacing / 2
    for i in range(num_lines_middle):
        y = y_offset_middle - i * line_spacing
        wg = c << straight(length=line_length, cross_section=xs)
        wg.move((0, y))
    
    return c


def my_device(**kwargs):
    """
    Wrapper function for my_device that creates a copy of the component.
    This avoids the "LockedError" when modifying a cached component.
    """
    return _my_device(**kwargs).copy()


device = my_device()

# Verify the device fits within footprint
#from gdsfactory.pdk import get_layer
#LAYER = get_layer()
# Define the bounding box layer
bbox_layer = (68, 0)
# Add a bounding box to the device
device = gf.add_padding(device, default=0, layers=(bbox_layer,))
device.show()
device.write_gds("my_device.gds")