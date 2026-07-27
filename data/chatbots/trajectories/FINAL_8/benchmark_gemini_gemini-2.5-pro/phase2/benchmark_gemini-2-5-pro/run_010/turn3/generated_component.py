import gdsfactory as gf
import numpy as np

@gf.cell
def create_device():
    """
    Creates the target device by correctly interpreting its geometry as three
    stacked components: a top U-shape, a central straight section, and a
    bottom (mirrored) U-shape.

    This version fixes a Pydantic ValidationError by using the correct API.
    Instead of passing a 'width' argument to CrossSection, we designate one
    of the inner Section objects to carry the ports by giving it 'port_names'.
    This enables port creation and allows the .connect() method to work.
    """
    # 1. Define Geometric Parameters based on visual analysis
    num_stripes = 5
    stripe_width = 0.5
    pitch = 1.0  # The distance between the centers of adjacent stripes
    layer = (1, 0)
    bend_radius = 6.0   # Increased radius to avoid self-intersection on inner stripes
    length_h_U = 60.0  # Horizontal length of the U-shape
    length_v_U = 15.0  # Vertical length of the U-shape's arms
    length_middle = 100.0 # Length of the central straight lines
    v_gap = 2.0  # Vertical gap between components

    # 2. Define the multi-stripe CrossSection
    sections = []
    center_offset = (num_stripes - 1) * pitch / 2
    # Designate the middle stripe to define the path for ports
    middle_stripe_index = num_stripes // 2

    for i in range(num_stripes):
        offset = i * pitch - center_offset
        if i == middle_stripe_index:
            # FIX: Assign port_names to this specific Section. This tells
            # gdsfactory where to create ports for any component using this XS.
            s = gf.Section(
                width=stripe_width,
                offset=offset,
                layer=layer,
                port_names=("o1", "o2"),
            )
        else:
            # Other sections do not get port names.
            s = gf.Section(width=stripe_width, offset=offset, layer=layer)
        sections.append(s)

    # The CrossSection is now correctly defined with a port carrier.
    xs_multi_stripe = gf.CrossSection(sections=sections)

    # 3. Create the fundamental U-shape component (opens upwards)
    u_shape = gf.Component("u_shape")
    s_h = u_shape << gf.components.straight(length=length_h_U, cross_section=xs_multi_stripe)
    b_left = u_shape << gf.components.bend_euler(radius=bend_radius, angle=90, cross_section=xs_multi_stripe)
    s_v_left = u_shape << gf.components.straight(length=length_v_U, cross_section=xs_multi_stripe)
    b_right = u_shape << gf.components.bend_euler(radius=bend_radius, angle=-90, cross_section=xs_multi_stripe)
    s_v_right = u_shape << gf.components.straight(length=length_v_U, cross_section=xs_multi_stripe)

    # Connect the primitives to form the U-shape
    b_left.connect('o1', s_h.ports['o1'])
    s_v_left.connect('o1', b_left.ports['o2'])
    b_right.connect('o1', s_h.ports['o2'])
    s_v_right.connect('o1', b_right.ports['o2'])

    # 4. Create the central straight component
    middle_straights = gf.components.straight(
        length=length_middle, cross_section=xs_multi_stripe
    )

    # 5. Assemble the final device by stacking the components
    c_final = gf.Component("final_device")
    
    middle_ref = c_final << middle_straights
    top_ref = c_final << u_shape
    bottom_ref = c_final << u_shape

    middle_ref.center = (0, 0)
    top_ref.centerx = 0
    top_ref.ymin = middle_ref.ymax + v_gap

    bottom_ref.mirror(p1=(0, 0), p2=(1, 0))
    bottom_ref.centerx = 0
    bottom_ref.ymax = middle_ref.ymin - v_gap

    return c_final

# Create an instance of the device for verification and output
device = create_device()

# This will generate the GDS file when the script is run.
device.write_gds("output.gds")