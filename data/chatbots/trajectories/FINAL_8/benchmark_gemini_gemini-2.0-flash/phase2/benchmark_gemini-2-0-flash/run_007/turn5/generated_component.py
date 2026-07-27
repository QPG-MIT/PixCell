import gdsfactory as gf
from gdsfactory.components import straight
from gdsfactory.cross_section import strip
from gdsfactory.path import straight as path_straight
from gdsfactory.path import Path


@gf.cell
def _my_device(
    num_lines_top=6,
    num_lines_bottom=6,
    num_lines_middle=7,
    line_length=120,
    line_spacing=0.4,
    line_width=0.4,  # width of each line at the center
    line_width_ends = 1.5,  #width of the line at the end.
    vertical_spacing=1.3,  # space between line groupings
    curve_radius = 10 #radius of curvature at line ends

):
    """
    Creates a device with three sections of parallel lines, tapering the lines at the ends.
    """
    c = gf.Component("my_device_internal")

    # Define the cross-section
    xs = strip(width=line_width, layer=(1, 0))
    xs_ends = strip(width = line_width_ends, layer = (1,0))

    # Create a transition
    taper_length = 5  # Length of the taper section

    #Top Section Path
    def top_path(length, radius):
      p = Path()
      p.append(path_straight(taper_length))
      p.append(gf.path.arc(radius=radius, angle=-10))
      p.append(path_straight(length - 2 * taper_length - 2*radius*0.1745))
      p.append(gf.path.arc(radius=radius, angle=-10))
      p.append(path_straight(taper_length))
      return p

    #Bottom Section Path
    def bottom_path(length, radius):
      p = Path()
      p.append(path_straight(taper_length))
      p.append(gf.path.arc(radius=radius, angle=10))
      p.append(path_straight(length - 2 * taper_length - 2*radius*0.1745))
      p.append(gf.path.arc(radius=radius, angle=10))
      p.append(path_straight(taper_length))
      return p


    # Top section
    y_offset_top = (num_lines_top - 1) * line_spacing / 2
    top_section_y = y_offset_top + vertical_spacing  # Shift top section up
    for i in range(num_lines_top):
        y = top_section_y - i * line_spacing
        path = top_path(line_length, curve_radius)
        transition = gf.path.transition(cross_section1=xs, cross_section2=xs_ends, width_type="linear")
        component = gf.path.extrude_transition(path, transition)
        wg = c << component
        wg.move((0, y))


    # Bottom section
    y_offset_bottom = (num_lines_bottom - 1) * line_spacing / 2
    bottom_section_y = -y_offset_bottom - vertical_spacing # Shift bottom section down
    for i in range(num_lines_bottom):
        y = bottom_section_y + i * line_spacing
        path = bottom_path(line_length, curve_radius)
        transition = gf.path.transition(cross_section1=xs, cross_section2=xs_ends, width_type="linear")
        component = gf.path.extrude_transition(path, transition)
        wg = c << component
        wg.move((0, y))


    # Middle section
    y_offset_middle = (num_lines_middle - 1) * line_spacing / 2
    for i in range(num_lines_middle):
        y = -y_offset_middle + i * line_spacing
        path = path_straight(line_length)
        transition = gf.path.transition(cross_section1=xs, cross_section2=xs_ends, width_type="linear")
        component = gf.path.extrude_transition(path, transition)
        wg = c << component
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
    line_width_ends = 1.5,
    vertical_spacing=1.3, # adjusted for optimal footprint
    curve_radius = 10
)

# Verify the device fits within footprint
bbox_layer = (68, 0)
device = gf.add_padding(device, default=0, layers=(bbox_layer,))
device.show()
device.write_gds("my_device.gds")