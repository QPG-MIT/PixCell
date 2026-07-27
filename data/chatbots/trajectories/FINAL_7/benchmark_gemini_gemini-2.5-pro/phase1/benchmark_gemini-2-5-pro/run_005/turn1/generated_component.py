import gdsfactory as gf

def create_device_from_image():
    """
    Recreates the device from the provided image using a subtractive
    boolean approach with parametric gdsfactory components.

    The overall shape is defined by a solid stadium primitive, from which
    all the internal features (holes) are subtracted.
    """

    # 1. Define overall dimensions from the provided footprint
    device_width = 5.5
    device_height = 3.0

    # 2. Create the solid base shape (the "blank")
    # The 'stadium' component is not in the catalog, so we construct it
    # by combining a rectangle and two circles.
    blank_component = gf.Component("stadium_blank")

    # The height of the stadium is its width. The radius of the ends is height/2.
    circle_radius = device_height / 2.0
    # The length of the central rectangular part is the total width minus the two radii.
    rect_length = device_width - (2 * circle_radius)

    # Create the primitive shapes
    center_rect = gf.components.rectangle(size=(rect_length, device_height))
    end_circle = gf.components.circle(radius=circle_radius)

    # Assemble the shapes into a single component.
    # Add the central rectangle (no move needed as it's centered at (0,0))
    blank_component << center_rect

    # Add the right-side circle, capture its reference, and move it into position
    circle_ref_right = blank_component << end_circle
    circle_ref_right.move((rect_length / 2, 0))

    # Add the left-side circle, capture its reference, and move it into position
    circle_ref_left = blank_component << end_circle
    circle_ref_left.move((-rect_length / 2, 0))


    # 3. Create a new component to hold all the cutout shapes (the "negative" space)
    cutouts = gf.Component("cutouts")

    # 4. Define and assemble the cutouts based on visual proportions
    # These parameters are estimated to match the visual appearance of the image
    central_gap_height = 0.4
    bar_height = 0.7
    # Use the calculated rectangle length for the stadium as the reference for the inner part
    central_gap_straight_length = 1.8
    taper_length = (rect_length + 0.2 - central_gap_straight_length) / 2.0 # Adjusted for visual fit
    taper_end_height = 2 * bar_height + central_gap_height

    # 4a. Construct the large central cutout from a rectangle and two tapers
    cut_center_rect = gf.components.rectangle(
        size=(central_gap_straight_length, central_gap_height)
    )
    cut_taper = gf.components.taper(
        length=taper_length, width1=central_gap_height, width2=taper_end_height
    )

    # Assemble the central cutout shape in a temporary component
    central_cutout_assembler = gf.Component("central_cutout_assembler")
    rect_ref = central_cutout_assembler << cut_center_rect
    taper_r = central_cutout_assembler << cut_taper
    taper_l = central_cutout_assembler << cut_taper
    taper_l.mirror()

    # Connect the pieces to form the full octagonal-like hole
    taper_r.connect("o1", rect_ref.ports["o2"])
    taper_l.connect("o1", rect_ref.ports["o1"])
    cutouts.add_ref(central_cutout_assembler) # Add the finished shape to the cutouts collection

    # 4b. Define and position the four small rectangular holes
    hole_width = 0.8
    hole_height = 0.35
    hole_primitive = gf.components.rectangle(size=(hole_width, hole_height))

    # Calculate positions based on symmetry
    hole_x_pos = central_gap_straight_length / 4.0
    hole_y_pos = central_gap_height / 2.0 + bar_height / 2.0

    # Add four references of the hole primitive to the cutouts component
    cutouts.add_ref(hole_primitive).move((+hole_x_pos, +hole_y_pos))  # Top-right
    cutouts.add_ref(hole_primitive).move((-hole_x_pos, +hole_y_pos))  # Top-left
    cutouts.add_ref(hole_primitive).move((+hole_x_pos, -hole_y_pos))  # Bottom-right
    cutouts.add_ref(hole_primitive).move((-hole_x_pos, -hole_y_pos))  # Bottom-left

    # 5. Perform the final boolean subtraction to create the device
    # The 'not' operation subtracts the 'cutouts' component from the 'blank_component'
    final_device = gf.boolean(A=blank_component, B=cutouts, operation="not")

    return final_device

# Instantiate the component.
# In a real workflow, you would now save this to a GDS file.
c = create_device_from_image()