import gdsfactory as gf
from gdsfactory.components import rectangle
from gdsfactory.components import straight
from gdsfactory.components import taper


@gf.cell
def create_device():
    c = gf.Component("my_device")

    # Define cross-section (example)
    xs = gf.cross_section.strip()  # Using default strip waveguide cross-section

    # Define dimensions based on the image analysis
    wg_width = xs.width  # Width of the waveguide
    strip_separation = 0.2  # Separation between the stripes
    strip_height = 1
    num_stripes_top = 5  # Number of stripes on top
    num_stripes_bottom = 5  # Number of stripes on the bottom
    num_stripes_middle = 5  # Number of stripes in the middle
    middle_gap_width = 120
    straight_extension = 5 # how much do we extend the outer straight sections over the main body

    # ############# Create Top Section ##############
    # Create the main body of the top block
    top_body = rectangle(size=(middle_gap_width, strip_height), centered=False)
    top_body_ref = c << top_body
    y_offset_top = (num_stripes_top - 1) * (wg_width + strip_separation) / 2
    top_body_ref.movey(y_offset_top)
    top_body_ref.movex(-middle_gap_width/2) #move the rectangle to the origin

    # Create the stripes for the top block
    for i in range(num_stripes_top):
        y_offset = i * (wg_width + strip_separation)
        
        # Add a horizontal waveguide to the left of the block
        left_wg = straight(length=straight_extension, cross_section=xs)
        left_wg_ref = c << left_wg
        left_wg_ref.connect("o2", top_body_ref.ports["e1"])
        left_wg_ref.movey(y_offset + top_body_ref.ysize/2) # offset relative to the top_body_ref
        left_wg_ref.movex(-middle_gap_width/2 - straight_extension)
        
        # Add a horizontal waveguide to the right of the block
        right_wg = straight(length=straight_extension, cross_section=xs)
        right_wg_ref = c << right_wg
        right_wg_ref.connect("o1", top_body_ref.ports["e2"])
        right_wg_ref.movey(y_offset + top_body_ref.ysize/2)  # offset relative to the top_body_ref
        right_wg_ref.movex(middle_gap_width/2)

    # ############# Create Middle Section ##############
    # Create the main body of the middle block
    middle_body = rectangle(size=(middle_gap_width, wg_width), centered=False)
    middle_body_ref = c << middle_body
    middle_body_ref.movex(-middle_gap_width/2)  #move the rectangle to the origin

    # Create the stripes for the middle block
    for i in range(num_stripes_middle):
        y_offset = (i - (num_stripes_middle - 1) / 2) * (wg_width + strip_separation)
        
        # Add a horizontal waveguide to the left of the block
        left_wg = straight(length=straight_extension, cross_section=xs)
        left_wg_ref = c << left_wg
        left_wg_ref.connect("o2", middle_body_ref.ports["e1"])
        left_wg_ref.movey(y_offset) # offset relative to the middle_body_ref
        left_wg_ref.movex(-middle_gap_width/2 - straight_extension)
        
        # Add a horizontal waveguide to the right of the block
        right_wg = straight(length=straight_extension, cross_section=xs)
        right_wg_ref = c << right_wg
        right_wg_ref.connect("o1", middle_body_ref.ports["e2"])
        right_wg_ref.movey(y_offset)  # offset relative to the middle_body_ref
        right_wg_ref.movex(middle_gap_width/2)

    # ############# Create Bottom Section ##############
    # Create the main body of the bottom block
    bottom_body = rectangle(size=(middle_gap_width, strip_height), centered=False)
    bottom_body_ref = c << bottom_body
    y_offset_bottom = (num_stripes_bottom - 1) * (wg_width + strip_separation) / 2
    bottom_body_ref.movey(-y_offset_bottom)
    bottom_body_ref.movex(-middle_gap_width/2)  #move the rectangle to the origin

    # Create the stripes for the bottom block
    for i in range(num_stripes_bottom):
        y_offset = i * (wg_width + strip_separation)
        
        # Add a horizontal waveguide to the left of the block
        left_wg = straight(length=straight_extension, cross_section=xs)
        left_wg_ref = c << left_wg
        left_wg_ref.connect("o2", bottom_body_ref.ports["e1"])
        left_wg_ref.movey(-y_offset - bottom_body_ref.ysize/2) # offset relative to the bottom_body_ref
        left_wg_ref.movex(-middle_gap_width/2 - straight_extension)
        
        # Add a horizontal waveguide to the right of the block
        right_wg = straight(length=straight_extension, cross_section=xs)
        right_wg_ref = c << right_wg
        right_wg_ref.connect("o1", bottom_body_ref.ports["e2"])
        right_wg_ref.movey(-y_offset - bottom_body_ref.ysize/2)  # offset relative to the bottom_body_ref
        right_wg_ref.movex(middle_gap_width/2)


    return c


# Create and display the device
device = create_device()
device.show(show_ports=False)